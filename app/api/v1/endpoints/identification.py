"""Coffee identification endpoint for photo-based extraction."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps.auth import ensure_user_exists
from app.core.logging import get_logger
from app.schemas.identification import CoffeeIdentificationResponse
from app.services.identification import identification_service

logger = get_logger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGES = 4


@router.post("", response_model=CoffeeIdentificationResponse)
async def identify_coffee(
    images: list[UploadFile] = File(..., description="Coffee bag/label photos (1-4 images, max 10MB each)"),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeeIdentificationResponse:
    """Identify coffee from uploaded bag/label photos.

    Sends the images to Claude Vision for structured data extraction.
    Returns identified coffee attributes for user review.
    """
    # Validate service is configured
    if not identification_service.is_configured:
        logger.error("Anthropic API key not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coffee identification service is not configured",
        )

    # Validate image count
    if len(images) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required",
        )
    if len(images) > MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_IMAGES} images allowed",
        )

    # Read and validate each image
    image_bytes_list: list[bytes] = []
    for i, image in enumerate(images):
        # Validate content type
        if image.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {i + 1}: unsupported file type '{image.content_type}'. "
                f"Allowed types: JPEG, PNG, WebP",
            )

        # Read and validate size
        content = await image.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {i + 1}: file size exceeds 10MB limit",
            )
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {i + 1}: file is empty",
            )

        image_bytes_list.append(content)

    logger.info("Processing coffee identification", user_id=user_id, image_count=len(image_bytes_list))

    try:
        result = await identification_service.identify(image_bytes_list)
        logger.info(
            "Coffee identification complete",
            user_id=user_id,
            coffee_name=result.coffee_name,
            roaster_name=result.roaster.name if result.roaster else None,
        )
        return result
    except ValueError as e:
        logger.warning("Identification failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not identify coffee from this image",
        ) from e
    except Exception as e:
        logger.error("Unexpected identification error", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during coffee identification",
        ) from e
