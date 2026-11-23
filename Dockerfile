# Hardened Multi-Stage Dockerfile (SRE Security Best Practices)
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Create non-root user for container security
RUN groupadd --gid 10001 sregroup && \
    useradd --uid 10001 --gid sregroup --shell /usr/sbin/nologin --create-home sreuser

WORKDIR /app

COPY --chown=sreuser:sregroup app/ ./app/

USER sreuser

EXPOSE 8080

# Built-in Container Liveness Healthcheck
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)" || exit 1

CMD ["python3", "-m", "app.main"]
