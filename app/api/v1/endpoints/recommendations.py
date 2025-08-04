from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user_id
from app.api.deps.database import get_db
from app.core.logging import get_logger
from app.services.recommendations.mvp_analyzer import MVPRecommendationAnalyzer

logger = get_logger(__name__)
router = APIRouter()


@router.get("/analysis")
async def get_flavor_analysis(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """MVP: Analyze user's coffee preferences using LLM."""

    try:
        analyzer = MVPRecommendationAnalyzer()
        analysis = await analyzer.analyze_user_preferences(
            current_user_id, db
        )

        return {
            "success": True,
            "analysis": analysis,
            "mvp_note": (
                "This is a flavor preference analysis. Coffee "
                "recommendations coming in future versions!"
            )
        }

    except ValueError as e:
        logger.error(f"Configuration error for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Recommendation service not properly configured"
        )
    except Exception as e:
        logger.error(
            f"Error analyzing preferences for user {current_user_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze coffee preferences"
        )


@router.get("/preferences")
async def get_user_taste_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Show user what their taste profile looks like."""

    try:
        from app.repositories.tasting import tasting_repository

        # Get user's tasting history
        tastings = await tasting_repository.get_by_user_id(
            db, current_user_id, limit=1000
        )

        if not tastings:
            return {
                "total_tastings": 0,
                "message": (
                    "No tasting data found. Start logging your coffee "
                    "tastings to build your taste profile!"
                )
            }
        
        # Simple analysis of user's tasting history
        flavor_frequency: dict[str, int] = {}
        total_ratings = []
        brew_methods: dict[str, int] = {}

        for tasting in tastings:
            # Collect overall ratings
            if tasting.overall_rating:
                total_ratings.append(tasting.overall_rating)

            # Track brew methods
            if tasting.brew_method:
                method = tasting.brew_method.value
                brew_methods[method] = brew_methods.get(method, 0) + 1

            # Count flavor frequencies
            for note in tasting.tasting_notes:
                flavor_name = note.flavor_tag.name
                flavor_frequency[flavor_name] = (
                    flavor_frequency.get(flavor_name, 0) + 1
                )
        
        # Calculate averages and sort
        avg_rating = (
            sum(total_ratings) / len(total_ratings) if total_ratings else 0
        )
        most_common_flavors = sorted(
            flavor_frequency.items(), key=lambda x: x[1], reverse=True
        )[:10]
        most_common_brew_methods = sorted(
            brew_methods.items(), key=lambda x: x[1], reverse=True
        )[:5]

        avg_rating_display = (
            round(avg_rating, 1) if avg_rating > 0 else "N/A"
        )

        return {
            "total_tastings": len(tastings),
            "average_rating": round(avg_rating, 1) if avg_rating > 0 else None,
            "most_common_flavors": most_common_flavors,
            "preferred_brew_methods": most_common_brew_methods,
            "taste_profile_summary": (
                f"Based on {len(tastings)} coffee tastings with an "
                f"average rating of {avg_rating_display}"
            )
        }
        
    except Exception as e:
        logger.error(
            f"Error getting taste profile for user {current_user_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve taste profile"
        )