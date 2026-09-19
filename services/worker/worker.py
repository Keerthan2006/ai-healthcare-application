import os
import time

import psycopg2
import redis
import requests
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)


REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ["POSTGRES_PORT"])
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DB = os.environ["POSTGRES_DB"]

EHR_URL = os.environ["EHR_SERVICE_URL"]

PROCESSING_TIME = float(os.environ["PROCESSING_TIME"])
MAX_ATTEMPTS = int(os.environ["MAX_ATTEMPTS"])


JOBS_PROCESSED = Counter(
    "worker_jobs_processed_total",
    "Total number of successfully processed jobs",
)

JOBS_FAILED = Counter(
    "worker_jobs_failed_total",
    "Total number of permanently failed jobs",
)

JOBS_RETRIED = Counter(
    "worker_jobs_retried_total",
    "Total number of job retries",
)

JOB_PROCESSING_TIME = Histogram(
    "worker_job_processing_seconds",
    "Time taken to process a job",
)

QUEUE_DEPTH = Gauge(
    "worker_queue_depth",
    "Number of jobs currently waiting in the healthcare queue",
)



start_http_server(8003)

print(
    "Worker metrics server started on port 8003",
    flush=True,
)


redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=None,
)



def update_queue_depth():

    try:

        queue_depth = redis_client.llen(
            "healthcare_jobs"
        )

        QUEUE_DEPTH.set(queue_depth)

        print(
            f"Current queue depth: {queue_depth}",
            flush=True,
        )

        return queue_depth

    except redis.exceptions.RedisError as error:

        print(
            f"Failed to get queue depth: {error}",
            flush=True,
        )

        return None


def update_job_status(job_id, status):

    connection = None

    try:

        connection = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            connect_timeout=5,
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE jobs
            SET status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
            """,
            (status, job_id),
        )

        connection.commit()

        cursor.close()

        print(
            f"Job {job_id} status updated to {status}",
            flush=True,
        )

    except psycopg2.Error as error:

        if connection:
            connection.rollback()

        print(
            f"Failed to update job {job_id} status: {error}",
            flush=True,
        )

    finally:

        if connection:
            connection.close()


# =========================
# Increment Job Attempt
# =========================

def increment_attempt(job_id):

    connection = None

    try:

        connection = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            connect_timeout=5,
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE jobs
            SET attempts = attempts + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
            RETURNING attempts
            """,
            (job_id,),
        )

        result = cursor.fetchone()

        connection.commit()

        cursor.close()

        attempts = result[0]

        print(
            f"Job {job_id} attempt "
            f"{attempts}/{MAX_ATTEMPTS}",
            flush=True,
        )

        return attempts

    except psycopg2.Error as error:

        if connection:
            connection.rollback()

        print(
            f"Failed to increment attempts "
            f"for {job_id}: {error}",
            flush=True,
        )

        return None

    finally:

        if connection:
            connection.close()


print(
    "Worker started",
    flush=True,
)



while True:

    try:


        update_queue_depth()



        print(
            "Waiting for jobs...",
            flush=True,
        )

        job = redis_client.blpop(
            "healthcare_jobs",
            timeout=5,
        )

        # No job available
        if not job:
            continue

        queue_name, job_id = job

        start = time.time()

        print(
            f"Job received: {job_id}",
            flush=True,
        )


        update_queue_depth()



        attempts = increment_attempt(job_id)

        if attempts is None:

            print(
                f"Could not determine attempt "
                f"count for {job_id}. "
                f"Requeueing.",
                flush=True,
            )

            redis_client.rpush(
                "healthcare_jobs",
                job_id,
            )

            update_queue_depth()

            time.sleep(2)

            continue



        update_job_status(
            job_id,
            "PROCESSING",
        )



        try:

            print(
                f"Processing job: {job_id}",
                flush=True,
            )

            # Simulate processing time
            time.sleep(PROCESSING_TIME)



            print(
                f"Calling EHR: {EHR_URL}/sync",
                flush=True,
            )

            response = requests.post(
                f"{EHR_URL}/sync",
                json={
                    "job_id": job_id,
                },
                timeout=5,
            )

            response.raise_for_status()

            print(
                f"EHR response: {response.status_code}",
                flush=True,
            )



            update_job_status(
                job_id,
                "COMPLETED",
            )

            JOBS_PROCESSED.inc()

            processing_time = (
                time.time() - start
            )

            JOB_PROCESSING_TIME.observe(
                processing_time
            )

            print(
                f"Job {job_id} completed "
                f"in {processing_time:.2f}s",
                flush=True,
            )


        except requests.RequestException as error:

            print(
                f"Job {job_id} failed: {error}",
                flush=True,
            )

            processing_time = (
                time.time() - start
            )

            JOB_PROCESSING_TIME.observe(
                processing_time
            )


            if attempts >= MAX_ATTEMPTS:

                print(
                    f"Job {job_id} reached "
                    f"maximum attempts "
                    f"({MAX_ATTEMPTS})",
                    flush=True,
                )

                update_job_status(
                    job_id,
                    "FAILED",
                )

                JOBS_FAILED.inc()

                print(
                    f"Job {job_id} "
                    f"permanently failed",
                    flush=True,
                )


            else:

                update_job_status(
                    job_id,
                    "FAILED",
                )

                print(
                    f"Retrying job {job_id} "
                    f"(attempt {attempts + 1} "
                    f"of {MAX_ATTEMPTS})",
                    flush=True,
                )

                redis_client.rpush(
                    "healthcare_jobs",
                    job_id,
                )

                JOBS_RETRIED.inc()

                update_queue_depth()

                time.sleep(2)

        update_queue_depth()



    except redis.exceptions.RedisError as error:

        print(
            f"Redis connection error: {error}",
            flush=True,
        )

        time.sleep(3)