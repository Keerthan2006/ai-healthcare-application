import asyncio
import os

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock EHR")


FAILURE_MODE = os.environ["EHR_FAILURE_MODE"]

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "mock-ehr",
        "mode": FAILURE_MODE
    }


@app.post("/sync")
async def sync(data: dict):

    job_id = data.get("job_id")

    print(
        f"EHR received job: {job_id}",
        flush=True
    )




    if FAILURE_MODE == "normal":

        print(
            "EHR NORMAL RESPONSE",
            flush=True
        )

        print(
            f"EHR successfully processed job: {job_id}",
            flush=True
        )

        return {
            "status": "success",
            "job_id": job_id
        }




    if FAILURE_MODE == "failure":

        print(
            "EHR TEMPORARY FAILURE SIMULATION",
            flush=True
        )

        raise HTTPException(
            status_code=503,
            detail="EHR temporarily unavailable"
        )




    if FAILURE_MODE == "slow":

        print(
            "EHR SLOW RESPONSE SIMULATION",
            flush=True
        )

        await asyncio.sleep(10)

        print(
            f"EHR successfully processed job: {job_id}",
            flush=True
        )

        return {
            "status": "success",
            "job_id": job_id
        }



    if FAILURE_MODE == "timeout":

        print(
            "EHR TIMEOUT SIMULATION",
            flush=True
        )

        await asyncio.sleep(30)

        return {
            "status": "success",
            "job_id": job_id
        }


    if FAILURE_MODE == "auth":

        print(
            "EHR AUTHENTICATION FAILURE",
            flush=True
        )

        raise HTTPException(
            status_code=401,
            detail="EHR authentication failed"
        )


    if FAILURE_MODE == "unavailable":

        print(
            "EHR UNAVAILABLE SIMULATION",
            flush=True
        )

        raise HTTPException(
            status_code=503,
            detail="EHR service unavailable"
        )


    if FAILURE_MODE == "unknown":

        print(
            "EHR UNKNOWN OUTCOME SIMULATION",
            flush=True
        )

        raise HTTPException(
            status_code=500,
            detail="EHR returned an unknown outcome"
        )


    print(
        f"Unknown EHR failure mode: {FAILURE_MODE}",
        flush=True
    )

    raise HTTPException(
        status_code=500,
        detail=f"Unknown EHR failure mode: {FAILURE_MODE}"
    )