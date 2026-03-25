"""Identification service for extracting coffee data from photos via Claude Vision."""

import base64
import io

from anthropic import AsyncAnthropic
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.identification import CoffeeIdentificationResponse

logger = get_logger(__name__)

# Claude's optimal max resolution
MAX_IMAGE_DIMENSION = 1568
JPEG_QUALITY = 85

SYSTEM_PROMPT = """\
You are a coffee identification assistant. You analyze photos of coffee bags, cards, and labels \
to extract structured product information.

Instructions:
- Extract ALL visible information from the photo(s).
- For each field, assess your confidence on a scale of 0 to 1. If your confidence is below 0.7, \
return null for that field. The user can always fill in missing values manually. \
Never guess or infer values that are not explicitly visible.
- For processing_method, only use one of these exact values: "washed", "natural", "honey", "anaerobic". \
If the bag mentions a processing method that does not match one of these exactly, use null.
- For roast_level, only use one of these exact values: "light", "medium", "medium_dark", "dark". \
If the roast level does not match one of these exactly, use null.
- For flavor_notes, extract each individual flavor as a separate entry. If the bag groups flavors \
by category (e.g., "Fruit: blueberry, strawberry"), include the category for each flavor. \
If no category grouping is visible, set category to null.
- Capture ALL readable text from the image in the raw_text field, including text that doesn't map \
to any specific field. This is for debugging and transparency.
- If multiple images are provided (e.g., front and back of bag), combine information from all images.
- For roast_date and best_by_date, extract the date string exactly as printed on the bag.
- The roaster location should be the city/region shown on the bag, not inferred from the roaster name.\
"""


def _resize_image(image_bytes: bytes) -> tuple[bytes, str]:
    """Resize an image to Claude's optimal resolution and convert to JPEG.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        Tuple of (processed JPEG bytes, media type string).
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB for JPEG
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if larger than max dimension
    width, height = img.size
    if max(width, height) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        logger.debug(
            "Resized image",
            original_size=f"{width}x{height}",
            new_size=f"{new_width}x{new_height}",
        )

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue(), "image/jpeg"


class IdentificationService:
    """Service for identifying coffee from bag/label photos using Claude Vision."""

    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            if not self.is_configured:
                raise ValueError("ANTHROPIC_API_KEY is not configured")
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if Anthropic is configured."""
        return bool(settings.ANTHROPIC_API_KEY)

    async def identify(self, images: list[bytes]) -> CoffeeIdentificationResponse:
        """Identify coffee from one or more bag/label photos.

        Args:
            images: List of raw image bytes (1-4 images).

        Returns:
            Structured coffee identification data.

        Raises:
            ValueError: If Anthropic is not configured or no tool use in response.
        """
        # Build content blocks: one image block per photo, then a text prompt
        content: list[dict] = []
        for i, image_bytes in enumerate(images):
            processed_bytes, media_type = _resize_image(image_bytes)
            image_data = base64.b64encode(processed_bytes).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })
            logger.debug("Prepared image", image_index=i, size_bytes=len(processed_bytes))

        content.append({
            "type": "text",
            "text": "Identify the coffee in this photo. Extract all visible information from the bag, card, or label.",
        })

        # Generate tool schema from the Pydantic model
        tool_schema = CoffeeIdentificationResponse.model_json_schema()

        logger.info("Sending identification request to Anthropic", image_count=len(images))

        response = await self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            tools=[{
                "name": "identify_coffee",
                "description": "Extract structured coffee information from the provided photo(s).",
                "input_schema": tool_schema,
            }],
            tool_choice={"type": "tool", "name": "identify_coffee"},
        )

        # Extract the tool use block
        for block in response.content:
            if block.type == "tool_use" and block.name == "identify_coffee":
                logger.info("Coffee identification successful")
                return CoffeeIdentificationResponse.model_validate(block.input)

        logger.warning("No tool use block in Anthropic response", response_content=str(response.content))
        raise ValueError("Could not identify coffee from this image")


# Global singleton
identification_service = IdentificationService()
