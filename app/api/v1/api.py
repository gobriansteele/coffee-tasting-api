from fastapi import APIRouter

from app.api.v1.endpoints import coffees, flavors, health, me, recommendations, roasters, tastings

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(roasters.router, prefix="/roasters", tags=["roasters"])
api_router.include_router(coffees.router, prefix="/coffees", tags=["coffees"])
api_router.include_router(flavors.router, prefix="/flavors", tags=["flavors"])
api_router.include_router(tastings.router, prefix="/tastings", tags=["tastings"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
