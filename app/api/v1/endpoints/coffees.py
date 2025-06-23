from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_coffees():
    """List all coffees."""
    return {"message": "Coffees endpoint - Coming soon"}


@router.post("/")
async def create_coffee():
    """Create a new coffee."""
    return {"message": "Create coffee - Coming soon"}


@router.get("/{coffee_id}")
async def get_coffee():
    """Get a specific coffee."""
    return {"message": "Get coffee - Coming soon"}