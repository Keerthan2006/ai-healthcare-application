import asyncio
import os

from fastapi import FastAPI

app = FastAPI(title="AI Agent Service")


# =========================
# Environment Variables
# =========================

# Configuration is injected through Docker Compose / Kubernetes.
# No secrets or hardcoded configuration values are stored here.

FAILURE_MODE = os.environ["FAILURE_MODE"]


# =========================
# Health Check
# =========================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "ai-service"
    }


# =========================
# AI Prediction
# =========================

@app.post("/predict")
async def predict(data: dict):

    # =========================
    # Failure Simulation
    # =========================

    if FAILURE_MODE.lower() == "true":

        return {
            "status": "failed",
            "reason": "AI service failure simulation"
        }


    # =========================
    # Simulate AI Processing
    # =========================

    await asyncio.sleep(0.2)


    # =========================
    # Successful Response
    # =========================

    return {
        "status": "success",
        "result": "mock-ai-result",
        "input": data
    }