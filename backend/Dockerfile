# ─────────────────────────────────────────────
#  Backend – Multi-stage Docker build
# ─────────────────────────────────────────────

# Stage 1: Build deps in isolated layer
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Lean production image
FROM python:3.12-slim AS runner
WORKDIR /app

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .

USER appuser
EXPOSE 8000

# 2 workers: safe for Render free tier (512 MB RAM).
# Upgrade to --workers 4 on Starter plan (2 GB RAM).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
