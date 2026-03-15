# ─────────────────────────────────────────────
#  ML Service – Multi-stage Docker build
# ─────────────────────────────────────────────

FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .

# Model artifacts volume mount point
RUN mkdir -p /app/artifacts && chown appuser:appgroup /app/artifacts
VOLUME ["/app/artifacts"]

USER appuser
EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
