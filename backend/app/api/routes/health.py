from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
