from typing import Any
import openai
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.tasting import tasting_repository

logger = get_logger(__name__)


class MVPRecommendationAnalyzer:
    """MVP recommendation analyzer using LLM for coffee preference analysis."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY must be configured for recommendations"
            )
        self.openai_client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    async def analyze_user_preferences(
        self, user_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Get user's tasting data and analyze with LLM."""

        # 1. Get all user tastings from PostgreSQL
        user_data = await self._get_user_tasting_summary(user_id, db)

        if user_data["total_tastings"] == 0:
            return {
                "user_id": user_id,
                "total_tastings": 0,
                "flavor_analysis": (
                    "No tasting data available. Start logging your coffee "
                    "tastings to get personalized recommendations!"
                ),
                "data_summary": user_data
            }

        # 2. Format for LLM analysis
        prompt = self._create_analysis_prompt(user_data)

        # 3. Send to LLM for analysis
        analysis = await self._get_llm_analysis(prompt)

        return {
            "user_id": user_id,
            "total_tastings": user_data["total_tastings"],
            "flavor_analysis": analysis,
            "data_summary": user_data
        }
    
    async def _get_user_tasting_summary(
        self, user_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Extract structured tasting data from PostgreSQL."""
        try:
            tastings = await tasting_repository.get_by_user_id_with_eager_loading(
                db, user_id
            )
            
            # Structure the data for LLM consumption
            tasting_summaries = []
            flavor_frequency: dict[str, int] = {}
            rating_by_flavor: dict[str, list[int]] = {}
            
            for tasting in tastings:
                # Coffee info
                coffee_info = {
                    "coffee_name": (
                        tasting.coffee.name if tasting.coffee else "Unknown"
                    ),
                    "roaster": (
                        tasting.coffee.roaster.name
                        if tasting.coffee and tasting.coffee.roaster
                        else "Unknown"
                    ),
                    "overall_rating": tasting.overall_rating,
                    "would_buy_again": tasting.would_buy_again,
                    "brew_method": (
                        tasting.brew_method.value
                        if tasting.brew_method
                        else "unknown"
                    ),
                    "session_notes": tasting.session_notes
                }
                
                # Flavor tags with intensity
                flavors_detected = []
                for note in tasting.tasting_notes:
                    flavor_info = {
                        "flavor": note.flavor_tag.name,
                        "category": note.flavor_tag.category,
                        "intensity": note.intensity,
                        "detected_in": {
                            "aroma": note.aroma,
                            "flavor": note.flavor,
                            "aftertaste": note.aftertaste
                        }
                    }
                    flavors_detected.append(flavor_info)
                    
                    # Track frequency and ratings
                    flavor_name = note.flavor_tag.name
                    flavor_frequency[flavor_name] = (
                        flavor_frequency.get(flavor_name, 0) + 1
                    )
                    if flavor_name not in rating_by_flavor:
                        rating_by_flavor[flavor_name] = []
                    if tasting.overall_rating:
                        rating_by_flavor[flavor_name].append(
                            tasting.overall_rating
                        )
                
                tasting_summaries.append({
                    "coffee": coffee_info,
                    "flavors": flavors_detected
                })
            
            return {
                "total_tastings": len(tastings),
                "tastings": tasting_summaries,
                "flavor_frequency": flavor_frequency,
                "average_rating_by_flavor": {
                    flavor: sum(ratings) / len(ratings)
                    for flavor, ratings in rating_by_flavor.items()
                    if ratings
                }
            }
        except Exception as e:
            logger.error(f"Error getting user tasting summary: {e}")
            raise
    
    def _create_analysis_prompt(self, user_data: dict[str, Any]) -> str:
        """Create a structured prompt for LLM analysis."""

        most_common = dict(
            list(user_data['flavor_frequency'].items())[:10]
        )
        prompt = f"""
Analyze this coffee taster's preferences based on their tasting history:

TASTING SUMMARY:
- Total tastings: {user_data['total_tastings']}
- Most common flavors: {most_common}
- Average ratings by flavor: {user_data['average_rating_by_flavor']}

DETAILED TASTING HISTORY:
"""
        
        # Add individual tasting details (limit to recent 10 for efficiency)
        for tasting in user_data['tastings'][:10]:
            coffee = tasting['coffee']
            flavors_str = [
                f"{f['flavor']} (intensity: {f['intensity']})"
                for f in tasting['flavors']
            ]
            prompt += f"""
Coffee: {coffee['coffee_name']} by {coffee['roaster']}
Rating: {coffee['overall_rating']}/10 | Would buy again: {coffee['would_buy_again']}
Brew method: {coffee['brew_method']}
Flavors detected: {flavors_str}
Notes: {coffee['session_notes'] or 'None'}
---
"""
        
        prompt += """
Based on this tasting history, provide a comprehensive analysis:

1. FLAVOR PREFERENCES: What flavor profiles does this person prefer?
2. INTENSITY PREFERENCES: Do they prefer subtle or bold flavors?
3. COFFEE STYLE: What types of coffees should they seek out?
4. BREWING RECOMMENDATIONS: Any patterns in their preferred brewing methods?
5. FLAVOR DISCOVERY: What new flavors might they enjoy?

Provide specific, actionable recommendations for their next coffee purchase.
Format your response in clear sections with specific recommendations.
"""
        
        return prompt
    
    async def _get_llm_analysis(self, prompt: str) -> str:
        """Send prompt to LLM and get analysis back."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective for MVP
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional coffee cupper and flavor "
                            "expert. Provide detailed, actionable analysis of "
                            "coffee preferences based on tasting data. Be "
                            "specific and helpful."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return (
                response.choices[0].message.content
                or "Unable to generate analysis."
            )
            
        except Exception as e:
            logger.error(f"Error getting LLM analysis: {e}")
            return f"Error analyzing preferences: {str(e)}"