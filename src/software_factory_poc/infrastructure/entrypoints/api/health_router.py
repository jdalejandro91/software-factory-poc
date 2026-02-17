from importlib.metadata import version

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        app_version = version("software-factory-poc")
    except Exception:
        app_version = "0.0.0"

    return {"status": "ok", "service": "software-factory-poc", "version": app_version}
