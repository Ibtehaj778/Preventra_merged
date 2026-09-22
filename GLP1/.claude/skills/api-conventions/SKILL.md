---
name: api-conventions
description: How to add or change an API endpoint in this project so backend and frontend stay consistent - router prefixes and tags, schemas, Mongo access, error handling, CORS, and the single frontend API surface. Use when adding, renaming, or removing an endpoint, creating a new router, or wiring a new call into the dashboard.
---

# API conventions

Adding an endpoint touches four places. Doing all four keeps the API self-describing and the
frontend working.

## 1. Router

One module per feature area in `Backend/routers/`. Namespace it:

```python
router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("")                 # -> /api/patients
@router.get("/{patient_idx}")   # -> /api/patients/{idx}
```

The prefix carries the area, the decorator carries the rest of the path. `tags` is what
groups the endpoint in the OpenAPI docs at `/docs` — without it the endpoint lands in an
untagged bucket.

**Known inconsistency:** only `chatbot` and `consequence` follow this. The other eight
routers use a bare `APIRouter()` with the full path in the decorator. New routers should use
the prefixed form. Converting an existing one is non-breaking — `prefix="/patients"` plus
`@router.get("")` serves the exact same URL — so the frontend needs no change. For
single-endpoint routers (`summary`, `survival`, `cost`, `budget`) a prefix buys little; just
add `tags`.

## 2. Schemas

Request and response models go in `Backend/schemas/<area>.py` as pydantic models. Always set
`response_model` on the route — it is what keeps internal fields from leaking into a
response. Model the public shape explicitly rather than returning the raw document:

```python
class UserPublic(BaseModel):     # no password_hash - it cannot leak if it isn't here
    id:    str
    email: str
```

Validate at the edge. Constraints belong on the pydantic field (`Field(min_length=8)`), not
on the form that happens to call it — a client-side rule is not a rule.

## 3. Data access and errors

Call `get_db()` from `core.mongo` inside the handler. There is no dependency-injection layer
and no session object:

```python
from core.mongo import get_db

async def handler():
    db = get_db()
    doc = await db.collection.find_one({...})
    if doc is None:
        raise HTTPException(status_code=404, detail="Not found")
```

Motor is async — every query needs `await`. Raise `HTTPException` for anything the caller
should see; let unexpected errors surface as 500s rather than swallowing them into a
misleading message.

Check-then-write is a race unless the database enforces it. If uniqueness matters, add a
unique index and catch the duplicate-key error; the pre-check is only there to produce a
friendlier message.

## 4. Mount it

```python
# Backend/main.py
from routers import summary, patients, ..., newthing
app.include_router(newthing.router, prefix="/api")
```

Everything is served under `/api`.

## 5. Frontend

Every call goes through `Frontend/src/data/api.js`. Add a method to the exported `api`
object — never call `fetch` from a component:

```js
export const api = {
  getPatients: (params) => get("/api/patients?" + new URLSearchParams(params)),
  clearChatSession: (id) => del(`/api/chatbot/session/${id}`),
};
```

The three helpers (`get`, `post`, `del`) throw on any non-2xx, so callers only handle the
happy path plus a catch.

## CORS

`main.py` currently allows `GET, POST, OPTIONS` only. **DELETE is missing**, which means
`api.js`'s `del()` fails cross-origin preflight. Adding a verb to the frontend means adding
it to `allow_methods` in the same change.

## Checklist

- [ ] Router has `prefix` and `tags`
- [ ] Request and response models in `schemas/`, `response_model` set on the route
- [ ] Response model exposes only what should be public
- [ ] Validation on the pydantic field, not just the UI
- [ ] `await` on every Motor call, `HTTPException` for caller-visible errors
- [ ] Router included in `main.py` under `/api`
- [ ] Method added to `api.js`, no `fetch` in components
- [ ] Verb present in `allow_methods`
- [ ] Endpoint shows under the right tag at `/docs`
