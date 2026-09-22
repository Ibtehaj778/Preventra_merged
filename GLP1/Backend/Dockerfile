# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall scikit-learn.
# requirements.txt ONLY - requirements-dev.txt pulls pandas, lifelines, shap,
# matplotlib and seaborn, none of which the API imports at runtime.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY routers/ ./routers/
COPY schemas/ ./schemas/
COPY main.py .

# core/loader.py reads these two off disk at startup; without them the model
# info and global SHAP endpoints fall back to defaults. The CSVs in this folder
# are seeder input, not runtime input - they are excluded by .dockerignore.
COPY data/final_gb_model.pkl data/shap_values_test.npy ./data/

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
