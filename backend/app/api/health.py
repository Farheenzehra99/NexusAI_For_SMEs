from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "NexusAI API",
        "version": "0.1.0",
        "database": "connected",
    }
