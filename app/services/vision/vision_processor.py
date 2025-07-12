"""Vision processing tools for image analysis and generation."""

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import cv2
import httpx
import numpy as np
import pytesseract

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ImageType(Enum):
    """Types of images the system can process."""
    DOCUMENT = "document"
    ROOM_PHOTO = "room_photo"
    FOOD_PHOTO = "food_photo"
    PERSON_PHOTO = "person_photo"
    RECEIPT = "receipt"
    QR_CODE = "qr_code"
    UNKNOWN = "unknown"


@dataclass
class VisionResult:
    """Result of vision processing."""
    image_type: ImageType
    text_content: Optional[str] = None
    objects_detected: List[Dict] = None
    qr_data: Optional[str] = None
    document_data: Optional[Dict] = None
    confidence: float = 0.0
    metadata: Dict = None


class VisionProcessor:
    """Process images for hotel operations."""

    def __init__(self):
        """Initialize vision processor."""
        self.ocr_languages = ['por', 'eng']  # Portuguese and English

        # Initialize QR code detector
        self.qr_detector = cv2.QRCodeDetector()

        # Document patterns for Brazilian documents
        self.document_patterns = {
            'cpf': r'\d{3}\.\d{3}\.\d{3}-\d{2}',
            'rg': r'\d{1,2}\.\d{3}\.\d{3}-\d{1,2}',
            'passport': r'[A-Z]{2}\d{6}',
            'phone': r'(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}'
        }

    async def process_image(self, image_url: str) -> VisionResult:
        """
        Process image from URL.
        
        Args:
            image_url: URL of the image to process
            
        Returns:
            VisionResult with extracted information
        """
        try:
            # Download image
            image_data = await self._download_image(image_url)

            # Convert to OpenCV format
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Detect image type
            image_type = await self._detect_image_type(img)

            # Process based on type
            if image_type == ImageType.DOCUMENT:
                return await self._process_document(img)
            elif image_type == ImageType.QR_CODE:
                return await self._process_qr_code(img)
            elif image_type == ImageType.RECEIPT:
                return await self._process_receipt(img)
            elif image_type == ImageType.ROOM_PHOTO:
                return await self._process_room_photo(img)
            else:
                # Default: extract any text
                text = self._extract_text(img)
                return VisionResult(
                    image_type=image_type,
                    text_content=text,
                    confidence=0.5
                )

        except Exception as e:
            logger.error("Error processing image", error=str(e))
            return VisionResult(
                image_type=ImageType.UNKNOWN,
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.content

    async def _detect_image_type(self, img: np.ndarray) -> ImageType:
        """Detect the type of image based on content."""
        # Check for QR code first
        qr_data, _, _ = self.qr_detector.detectAndDecode(img)
        if qr_data:
            return ImageType.QR_CODE

        # Extract text to analyze content
        text = self._extract_text(img).lower()

        # Check for document keywords
        doc_keywords = ['cpf', 'rg', 'identidade', 'passport', 'carteira', 'cnh']
        if any(keyword in text for keyword in doc_keywords):
            return ImageType.DOCUMENT

        # Check for receipt keywords
        receipt_keywords = ['total', 'subtotal', 'valor', 'cupom', 'fiscal', 'nf-e']
        if any(keyword in text for keyword in receipt_keywords):
            return ImageType.RECEIPT

        # Check image characteristics for room photos
        if self._looks_like_room(img):
            return ImageType.ROOM_PHOTO

        return ImageType.UNKNOWN

    def _extract_text(self, img: np.ndarray) -> str:
        """Extract text from image using OCR."""
        # Preprocess image for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Extract text
        text = pytesseract.image_to_string(
            thresh,
            lang='+'.join(self.ocr_languages)
        )

        return text.strip()

    async def _process_document(self, img: np.ndarray) -> VisionResult:
        """Process document image (ID, passport, etc)."""
        # Extract text
        text = self._extract_text(img)

        # Extract document data
        import re
        document_data = {}

        # Extract CPF
        cpf_match = re.search(self.document_patterns['cpf'], text)
        if cpf_match:
            document_data['cpf'] = cpf_match.group()

        # Extract RG
        rg_match = re.search(self.document_patterns['rg'], text)
        if rg_match:
            document_data['rg'] = rg_match.group()

        # Extract name (simple heuristic - lines with only letters)
        lines = text.split('\n')
        for line in lines:
            if line.strip() and line.isupper() and len(line) > 10:
                if 'nome' not in line.lower():
                    document_data['name'] = line.strip()
                    break

        # Extract dates
        date_pattern = r'\d{2}/\d{2}/\d{4}'
        dates = re.findall(date_pattern, text)
        if dates:
            document_data['dates_found'] = dates

        return VisionResult(
            image_type=ImageType.DOCUMENT,
            text_content=text,
            document_data=document_data,
            confidence=0.8 if document_data else 0.3
        )

    async def _process_qr_code(self, img: np.ndarray) -> VisionResult:
        """Process QR code image."""
        qr_data, points, _ = self.qr_detector.detectAndDecode(img)

        if qr_data:
            # Parse QR data
            metadata = {}

            # Check if it's a PIX QR code
            if 'pix' in qr_data.lower() or qr_data.startswith('00020126'):
                metadata['qr_type'] = 'pix'
                # TODO: Parse PIX data

            # Check if it's a URL
            elif qr_data.startswith(('http://', 'https://')):
                metadata['qr_type'] = 'url'
                metadata['url'] = qr_data

            # Check if it's a reservation code
            elif len(qr_data) < 20 and qr_data.isalnum():
                metadata['qr_type'] = 'reservation_code'
                metadata['code'] = qr_data

            return VisionResult(
                image_type=ImageType.QR_CODE,
                qr_data=qr_data,
                confidence=1.0,
                metadata=metadata
            )

        return VisionResult(
            image_type=ImageType.QR_CODE,
            confidence=0.0,
            metadata={"error": "QR code not detected"}
        )

    async def _process_receipt(self, img: np.ndarray) -> VisionResult:
        """Process receipt image."""
        text = self._extract_text(img)

        # Extract receipt data
        receipt_data = {}

        # Extract total amount
        total_pattern = r'(?:total|valor total)[\s:]*(?:r\$)?\s*([\d.,]+)'
        total_match = re.search(total_pattern, text.lower())
        if total_match:
            receipt_data['total'] = total_match.group(1)

        # Extract date
        date_pattern = r'\d{2}/\d{2}/\d{4}'
        date_match = re.search(date_pattern, text)
        if date_match:
            receipt_data['date'] = date_match.group()

        # Extract establishment name (usually in first lines)
        lines = text.split('\n')
        for line in lines[:5]:
            if len(line) > 10 and not any(char.isdigit() for char in line):
                receipt_data['establishment'] = line.strip()
                break

        return VisionResult(
            image_type=ImageType.RECEIPT,
            text_content=text,
            document_data=receipt_data,
            confidence=0.7 if receipt_data else 0.3
        )

    async def _process_room_photo(self, img: np.ndarray) -> VisionResult:
        """Process room photo for analysis."""
        # Use OpenAI Vision API or similar for room analysis
        if settings.openai_api_key:
            room_analysis = await self._analyze_room_with_ai(img)
            return VisionResult(
                image_type=ImageType.ROOM_PHOTO,
                objects_detected=room_analysis.get('objects', []),
                metadata=room_analysis,
                confidence=0.9
            )

        # Fallback: basic object detection
        objects = self._detect_room_objects(img)
        return VisionResult(
            image_type=ImageType.ROOM_PHOTO,
            objects_detected=objects,
            confidence=0.5
        )

    def _looks_like_room(self, img: np.ndarray) -> bool:
        """Check if image looks like a room photo."""
        # Simple heuristics
        height, width = img.shape[:2]

        # Room photos are usually landscape
        if width < height:
            return False

        # Check for typical room colors (browns, whites, beiges)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Define color ranges for typical room colors
        lower_brown = np.array([10, 20, 20])
        upper_brown = np.array([20, 255, 200])

        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])

        # Create masks
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        white_mask = cv2.inRange(hsv, lower_white, upper_white)

        # Calculate percentages
        brown_percent = np.count_nonzero(brown_mask) / (height * width)
        white_percent = np.count_nonzero(white_mask) / (height * width)

        # Room photos typically have these colors
        return (brown_percent + white_percent) > 0.3

    def _detect_room_objects(self, img: np.ndarray) -> List[Dict]:
        """Basic object detection for room features."""
        objects = []

        # Detect beds (simplified - look for rectangular shapes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 10000:  # Large objects
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h

                # Bed-like aspect ratio
                if 1.5 < aspect_ratio < 3:
                    objects.append({
                        'type': 'bed',
                        'confidence': 0.6,
                        'bbox': [x, y, w, h]
                    })

        return objects

    async def _analyze_room_with_ai(self, img: np.ndarray) -> Dict:
        """Use AI to analyze room photo."""
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # TODO: Call OpenAI Vision API
        # For now, return mock data
        return {
            'objects': [
                {'type': 'bed', 'count': 2, 'confidence': 0.9},
                {'type': 'tv', 'count': 1, 'confidence': 0.8},
                {'type': 'window', 'count': 1, 'confidence': 0.7}
            ],
            'room_type': 'superior',
            'cleanliness': 'excellent',
            'style': 'modern'
        }

    async def generate_room_suggestion_image(
            self,
            room_type: str,
            features: List[str]
    ) -> Optional[str]:
        """Generate room suggestion image using AI."""
        if not settings.openai_api_key:
            return None

        try:
            # TODO: Use DALL-E API to generate custom room image
            # For now, return placeholder
            return f"https://hotelpassarim.com.br/images/{room_type}-suggestion.jpg"

        except Exception as e:
            logger.error("Error generating image", error=str(e))
            return None

    def extract_document_for_checkin(self, document_data: Dict) -> Dict:
        """Extract and validate document data for check-in."""
        required_fields = ['name', 'cpf']
        missing_fields = [f for f in required_fields if f not in document_data]

        if missing_fields:
            return {
                'valid': False,
                'missing_fields': missing_fields,
                'message': f"Não consegui identificar: {', '.join(missing_fields)}"
            }

        # Validate CPF
        cpf = document_data['cpf'].replace('.', '').replace('-', '')
        if not self._validate_cpf(cpf):
            return {
                'valid': False,
                'errors': ['CPF inválido'],
                'message': "O CPF informado parece estar incorreto"
            }

        return {
            'valid': True,
            'data': {
                'name': document_data['name'],
                'cpf': document_data['cpf'],
                'document_type': 'cpf'
            },
            'message': "Documento validado com sucesso!"
        }

    def _validate_cpf(self, cpf: str) -> bool:
        """Validate Brazilian CPF."""
        if len(cpf) != 11 or not cpf.isdigit():
            return False

        # CPF validation algorithm
        nums = [int(d) for d in cpf]

        # Validate first digit
        sum1 = sum(nums[i] * (10 - i) for i in range(9))
        digit1 = (sum1 * 10) % 11
        if digit1 == 10:
            digit1 = 0

        if digit1 != nums[9]:
            return False

        # Validate second digit
        sum2 = sum(nums[i] * (11 - i) for i in range(10))
        digit2 = (sum2 * 10) % 11
        if digit2 == 10:
            digit2 = 0

        return digit2 == nums[10]
