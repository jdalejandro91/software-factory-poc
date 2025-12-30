from fastapi import APIRouter
from importlib.metadata import version

router = APIRouter()

@router.get("/health")
def health_check():
    try:
        app_version = version("software-factory-poc")
    except Exception:
        app_version = "0.0.0"
        
    return {
        "status": "ok",
        "service": "software-factory-poc",
        "version": app_version
    }
