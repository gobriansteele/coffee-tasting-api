from fastapi import APIRouter

from app.api.v1.endpoints import coffees, health, roasters, tastings

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(roasters.router, prefix="/roasters", tags=["roasters"])
api_router.include_router(coffees.router, prefix="/coffees", tags=["coffees"])
api_router.include_router(tastings.router, prefix="/tastings", tags=["tastings"])
