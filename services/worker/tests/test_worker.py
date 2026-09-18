import ast
from pathlib import Path

WORKER_FILE = Path(__file__).parent.parent / "worker.py"


def test_worker_source_compiles():
    source = WORKER_FILE.read_text()
    ast.parse(source)


def test_worker_contains_required_metrics():
    source = WORKER_FILE.read_text()

    assert "worker_jobs_processed_total" in source
    assert "worker_jobs_failed_total" in source
    assert "worker_jobs_retried_total" in source
    assert "worker_job_processing_seconds" in source


def test_worker_contains_retry_configuration():
    source = WORKER_FILE.read_text()

    assert "MAX_ATTEMPTS" in source
    assert "healthcare_jobs" in source


def test_worker_contains_ehr_integration():
    source = WORKER_FILE.read_text()

    assert "EHR_SERVICE_URL" in source
    assert "/sync" in source