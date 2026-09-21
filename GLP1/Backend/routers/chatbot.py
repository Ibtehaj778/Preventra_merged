"""
Chatbot endpoint. Runs a tool-call loop against Gemini:

  POST /api/chatbot/message      → send message, receive reply
  GET  /api/chatbot/session/{id} → fetch history
  DEL  /api/chatbot/session/{id} → clear history

Session history is kept in an in-memory dict for v1 (24h TTL, 1000 sessions LRU).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import OrderedDict

from fastapi import APIRouter, HTTPException

from core import chatbot_tools, llm
from core.config import settings
from schemas.chatbot import ChatRequest, ChatResponse, ToolCallLog

logger = logging.getLogger("chatbot.router")

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

_MAX_SESSIONS = 1000
_SESSION_TTL_SECONDS = 60 * 60 * 24
_MAX_HISTORY_MESSAGES = 20
_MAX_TOOL_ITERATIONS = 5

_SESSIONS: "OrderedDict[str, dict]" = OrderedDict()


def _evict_expired() -> None:
    now = time.monotonic()
    stale = [sid for sid, s in _SESSIONS.items() if now - s["touched"] > _SESSION_TTL_SECONDS]
    for sid in stale:
        _SESSIONS.pop(sid, None)
    while len(_SESSIONS) > _MAX_SESSIONS:
        _SESSIONS.popitem(last=False)


def _touch(session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if session is None:
        session = {"messages": [], "touched": time.monotonic()}
        _SESSIONS[session_id] = session
    else:
        session["touched"] = time.monotonic()
        _SESSIONS.move_to_end(session_id)
    return session


def _trim(messages: list[dict]) -> list[dict]:
    if len(messages) <= _MAX_HISTORY_MESSAGES:
        return messages
    return messages[-_MAX_HISTORY_MESSAGES:]


@router.post("/message", response_model=ChatResponse)
async def post_message(req: ChatRequest) -> ChatResponse:
    if not settings.chatbot_enabled:
        raise HTTPException(status_code=503, detail="Chatbot is disabled.")

    session_id = req.session_id or uuid.uuid4().hex
    _evict_expired()
    session = _touch(session_id)

    latest_user = req.messages[-1]
    if latest_user.role != "user":
        raise HTTPException(status_code=400, detail="Last message must have role='user'.")

    if not session["messages"]:
        for m in req.messages:
            session["messages"].append({"role": m.role, "content": m.content})
    else:
        session["messages"].append({"role": "user", "content": latest_user.content})

    try:
        system_instruction = await chatbot_tools.build_system_instruction(req.role_context)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Snapshot build failed")
        system_instruction = chatbot_tools._BASE_SYSTEM_PROMPT

    tool_calls_log: list[ToolCallLog] = []
    conversation = list(session["messages"])

    reply_text = ""
    error: str | None = None

    try:
        for _ in range(_MAX_TOOL_ITERATIONS):
            response = await llm.chat(
                messages=_trim(conversation),
                tools=[chatbot_tools.TOOL_SET],
                system_instruction=system_instruction,
            )

            function_calls = response["function_calls"]

            if not function_calls:
                reply_text = response["text"] or "(No response.)"
                break

            conversation.append({
                "role": "assistant",
                "content": response["text"] or "",
                "function_calls": function_calls,
                "model_content": response.get("model_content"),
            })

            for call in function_calls:
                result, err = await chatbot_tools.dispatch_tool(call["name"], call["args"])
                tool_calls_log.append(ToolCallLog(
                    name=call["name"],
                    args=call["args"],
                    ok=err is None,
                    error=err,
                ))
                conversation.append({
                    "role": "function",
                    "name": call["name"],
                    "response": result,
                })
        else:
            reply_text = (
                "I gathered several pieces of data but couldn't finish the answer within the "
                "tool-call limit. Try rephrasing or asking one thing at a time."
            )
    except RuntimeError as exc:
        logger.error("Chatbot config error: %s", exc)
        reply_text = (
            "The assistant isn't configured yet — the backend is missing `GOOGLE_API_KEY`. "
            "Add it to `Backend/.env` and restart the server."
        )
        error = str(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chatbot request failed")
        reply_text = "Sorry — I hit an error reaching the assistant. Please try again in a moment."
        error = f"{type(exc).__name__}: {exc}"

    session["messages"].append({"role": "assistant", "content": reply_text})
    session["touched"] = time.monotonic()

    return ChatResponse(
        reply=reply_text,
        session_id=session_id,
        tool_calls=tool_calls_log,
        error=error,
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    _SESSIONS.move_to_end(session_id)
    session["touched"] = time.monotonic()
    visible = [m for m in session["messages"] if m.get("role") in ("user", "assistant") and m.get("content")]
    return {"session_id": session_id, "messages": visible}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    existed = _SESSIONS.pop(session_id, None) is not None
    return {"cleared": existed, "session_id": session_id}
