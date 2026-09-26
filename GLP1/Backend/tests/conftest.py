import os

# core.config.Settings requires these at import time. Point the database at
# nothing, briefly, so no test can reach a real cluster by accident.
os.environ.setdefault("MONGODB_URI", "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100")
os.environ.setdefault("SHARED_SECRET_KEY", "test-secret-not-the-real-one")
