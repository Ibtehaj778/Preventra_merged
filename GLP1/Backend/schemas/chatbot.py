from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role:    Literal["user", "assistant"]
    content: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    messages:     List[ChatMessage] = Field(..., min_length=1, max_length=40)
    session_id:   Optional[str] = None
    # Ignored. The audience now comes from the signed-in account (see
    # routers/chatbot.py). Still accepted so an older frontend that sends it
    # is not refused.
    role_context: Optional[str] = None


class ToolCallLog(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)
    ok:   bool = True
    error: Optional[str] = None


class ChatResponse(BaseModel):
    reply:      str
    session_id: str
    tool_calls: List[ToolCallLog] = Field(default_factory=list)
    error:      Optional[str] = None
