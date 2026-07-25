FROM python:3.14-slim AS base

LABEL maintainer="TITAN Team"
LABEL description="TITAN - Institutional Trading Intelligence System"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TITAN_ENVIRONMENT=production

WORKDIR /app

FROM base AS deps

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM deps AS production

COPY titan/ titan/
COPY data/ data/

RUN groupadd -r titan && useradd -r -g titan -d /app -s /sbin/nologin titan && \
    mkdir -p logs data && \
    chown -R titan:titan /app

USER titan

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import titan; print('healthy')" || exit 1

ENTRYPOINT ["python", "-m", "titan"]
CMD ["status"]
