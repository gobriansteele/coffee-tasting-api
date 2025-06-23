from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_tasting_sessions():
    """List all tasting sessions."""
    return {"message": "Tasting sessions endpoint - Coming soon"}


@router.post("/")
async def create_tasting_session():
    """Create a new tasting session."""
    return {"message": "Create tasting session - Coming soon"}


@router.get("/{session_id}")
async def get_tasting_session():
    """Get a specific tasting session."""
    return {"message": "Get tasting session - Coming soon"}