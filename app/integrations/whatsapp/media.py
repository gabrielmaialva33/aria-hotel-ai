"""Media handling for WhatsApp messages."""

import base64
import io
from typing import Dict, Optional, Tuple

import httpx
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MediaHandler:
    """Handle media files from WhatsApp messages."""
    
    # Hotel images for sending
    HOTEL_IMAGES = {
        "exterior": "https://hotelpassarim.com.br/images/hotel-exterior.jpg",
        "room_terreo": "https://hotelpassarim.com.br/images/room-terreo.jpg",
        "room_superior": "https://hotelpassarim.com.br/images/room-superior.jpg",
        "pool": "https://hotelpassarim.com.br/images/pool.jpg",
        "lake": "https://hotelpassarim.com.br/images/lake.jpg",
        "restaurant": "https://hotelpassarim.com.br/images/restaurant.jpg",
        "breakfast": "https://hotelpassarim.com.br/images/breakfast.jpg",
        "pasta": "https://hotelpassarim.com.br/images/pasta-rotation.jpg"
    }
    
    def __init__(self):
        """Initialize media handler."""
        self.http_client = httpx.AsyncClient(
            headers={
                "User-Agent": "ARIA Hotel AI/1.0"
            },
            timeout=30.0
        )
    
    async def download_media(
        self,
        media_url: str,
        auth_token: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Download media from URL.
        
        Args:
            media_url: URL of the media file
            auth_token: Optional auth token for Twilio media
            
        Returns:
            Tuple of (content_bytes, content_type)
        """
        try:
            # Add auth header if token provided
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            # Download media
            response = await self.http_client.get(media_url, headers=headers)
            response.raise_for_status()
            
            content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")
            
            logger.info(
                "Media downloaded",
                url=media_url,
                size=len(content),
                content_type=content_type
            )
            
            return content, content_type
            
        except Exception as e:
            logger.error(
                "Failed to download media",
                url=media_url,
                error=str(e)
            )
            raise
    
    async def process_image(
        self,
        image_data: bytes,
        max_size: Tuple[int, int] = (1024, 1024)
    ) -> Dict:
        """
        Process image for analysis.
        
        Args:
            image_data: Raw image bytes
            max_size: Maximum dimensions for resizing
            
        Returns:
            Processed image info
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Get original info
            original_size = image.size
            original_mode = image.mode
            
            # Convert to RGB if needed
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            
            # Resize if needed
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)
            processed_data = output.getvalue()
            
            # Encode to base64 for vision models
            base64_image = base64.b64encode(processed_data).decode("utf-8")
            
            return {
                "original_size": original_size,
                "processed_size": image.size,
                "original_mode": original_mode,
                "data": processed_data,
                "base64": base64_image,
                "mime_type": "image/jpeg"
            }
            
        except Exception as e:
            logger.error("Failed to process image", error=str(e))
            raise
    
    def get_hotel_images(self, category: str = "general") -> list[str]:
        """
        Get hotel images for a category.
        
        Args:
            category: Image category (general, rooms, amenities, food)
            
        Returns:
            List of image URLs
        """
        categories = {
            "general": ["exterior", "pool", "lake"],
            "rooms": ["room_terreo", "room_superior"],
            "amenities": ["pool", "lake", "restaurant"],
            "food": ["breakfast", "pasta", "restaurant"]
        }
        
        image_keys = categories.get(category, ["exterior"])
        return [self.HOTEL_IMAGES[key] for key in image_keys if key in self.HOTEL_IMAGES]
    
    async def analyze_guest_image(self, image_data: bytes) -> Dict:
        """
        Analyze image sent by guest (e.g., for special requests).
        
        Args:
            image_data: Image bytes
            
        Returns:
            Analysis results
        """
        # Process image
        processed = await self.process_image(image_data)
        
        # TODO: Integrate with vision model for analysis
        # For now, return basic info
        return {
            "type": "guest_image",
            "size": processed["original_size"],
            "description": "Imagem recebida do hóspede",
            "requires_human_review": True
        }
    
    def format_media_response(self, media_type: str) -> Dict:
        """
        Format media response based on request type.
        
        Args:
            media_type: Type of media requested
            
        Returns:
            Response with text and media URLs
        """
        responses = {
            "hotel_photos": {
                "text": "📸 Aqui estão algumas fotos do nosso hotel!",
                "media": self.get_hotel_images("general")
            },
            "room_photos": {
                "text": "🏨 Estas são as fotos dos nossos apartamentos:",
                "media": self.get_hotel_images("rooms")
            },
            "amenities_photos": {
                "text": "✨ Nossa estrutura de lazer para você aproveitar:",
                "media": self.get_hotel_images("amenities")
            },
            "restaurant_photos": {
                "text": "🍽️ Conheça nosso restaurante e gastronomia:",
                "media": self.get_hotel_images("food")
            }
        }
        
        return responses.get(media_type, {
            "text": "Desculpe, não encontrei fotos dessa categoria.",
            "media": []
        })
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()
