from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core import loader, mongo
from core.model import init_startup_caches
from routers import summary, patients, segments, survival, cost, budget, shap, info, consequence, chatbot


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo.get_client()
    await mongo.ping()
    print(f"🔌  Connected to MongoDB: {settings.mongodb_db_name}")
    loader.load_binary_artifacts()
    await init_startup_caches()
    yield
    mongo.close_client()


# This service does NOT issue tokens. The Readmissions API is the single issuer
# for both products (its /auth/* endpoints, backed by `shared_identity.users`).
# Here we only VERIFY, in core/security.py, with the same SHARED_SECRET_KEY.
# A second issuer is what produced two accounts systems with differing
# `app_access` rules, so do not re-add one.
app = FastAPI(
    title="GLP-1 Analytics API",
    description="Backend for the GLP-1 Adherence & Cost Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(summary.router,  prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(segments.router, prefix="/api")
app.include_router(survival.router, prefix="/api")
app.include_router(cost.router,     prefix="/api")
app.include_router(budget.router,   prefix="/api")
app.include_router(shap.router,     prefix="/api")
app.include_router(info.router,     prefix="/api")
app.include_router(consequence.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
