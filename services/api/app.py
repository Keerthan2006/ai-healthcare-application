import os
import time
import uuid

import httpx
import psycopg2
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from database import get_connection

app = FastAPI(title="Healthcare API")


# =========================
# Environment Variables
# =========================

# All configuration is injected through Docker Compose / Kubernetes.
# No credentials or environment-specific values are hardcoded here.

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ["POSTGRES_PORT"])
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DB = os.environ["POSTGRES_DB"]

AI_SERVICE_URL = os.environ["AI_SERVICE_URL"]


# =========================
# Prometheus Metrics
# =========================

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
)


# =========================
# Metrics Middleware
# =========================

@app.middleware("http")
async def metrics_middleware(request, call_next):

    start = time.time()

    response = await call_next(request)

    latency = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(latency)

    return response


# =========================
# Health Check
# =========================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "api",
    }


# =========================
# Readiness Check
# =========================

@app.get("/ready")
def ready():

    try:

        # Check Redis
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            socket_connect_timeout=2,
        )

        redis_client.ping()

        # Check PostgreSQL
        connection = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            connect_timeout=2,
        )

        connection.close()

        return {
            "status": "ready",
        }

    except (redis.RedisError, psycopg2.Error) as error:

        raise HTTPException(
            status_code=503,
            detail=str(error),
        )


# =========================
# API Status
# =========================

@app.get("/api/v1/status")
def status():

    return {
        "service": "healthcare-api",
        "version": "v1",
        "status": "running",
    }


# =========================
# AI Request
# =========================

@app.post("/api/v1/ai")
async def ai_request():

    start = time.time()

    async with httpx.AsyncClient(timeout=5) as client:

        response = await client.post(
            f"{AI_SERVICE_URL}/predict",
            json={
                "request_id": str(uuid.uuid4()),
                "data": "sample-healthcare-input",
            },
        )

    return {
        "ai_response": response.json(),
        "latency_ms": round(
            (time.time() - start) * 1000,
            2,
        ),
    }


# =========================
# Create Job
# =========================

@app.post("/api/v1/jobs")
def create_job():

    job_id = str(uuid.uuid4())

    connection = None

    try:

        # Store job in PostgreSQL
        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO jobs (job_id, status)
            VALUES (%s, %s)
            """,
            (job_id, "QUEUED"),
        )

        connection.commit()

        cursor.close()

    except psycopg2.Error as error:

        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}",
        )

    finally:

        if connection:
            connection.close()

    # Add job to Redis queue
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )

    redis_client.rpush(
        "healthcare_jobs",
        job_id,
    )

    return {
        "job_id": job_id,
        "status": "queued",
    }


# =========================
# Queue Status
# =========================

@app.get("/api/v1/queue")
def queue_status():

    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
    )

    depth = redis_client.llen("healthcare_jobs")

    return {
        "queue": "healthcare_jobs",
        "depth": depth,
    }


# =========================
# Prometheus Metrics
# =========================

@app.get("/metrics")
def metrics():

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )