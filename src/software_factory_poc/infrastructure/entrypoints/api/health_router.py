from importlib.metadata import version

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        app_version = version("software-factory-poc")
    except Exception:
        app_version = "0.0.0"

    return {"status": "ok", "service": "software-factory-poc", "version": app_version}


@router.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics in text format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
