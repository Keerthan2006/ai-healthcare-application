import asyncio
import os

from fastapi import FastAPI

app = FastAPI(title="AI Agent Service")


FAILURE_MODE = os.environ["FAILURE_MODE"]


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "ai-service"
    }


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


    await asyncio.sleep(0.2)


    return {
        "status": "success",
        "result": "mock-ai-result",
        "input": data
    }