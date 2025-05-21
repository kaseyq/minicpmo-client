import base64
import logging
from PIL import Image
from io import BytesIO
import os


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    pass

class ImageProcessor:
    """Handles image processing operations."""
    @staticmethod
    def process_image(file_path: str) -> str:
        """Validate and encode image to base64."""
        try:
            with Image.open(file_path) as img:
                if img.format not in ['PNG', 'JPEG']:
                    raise ImageProcessingError(f"Unsupported image format: {img.format}. Use PNG or JPEG.")
                img.verify()  # Check for corruption
                img = Image.open(file_path)  # Reopen after verify
                img.thumbnail((1024, 1024))  # Resize if too large
                buffer = BytesIO()
                img.save(buffer, format=img.format)
                image_data = buffer.getvalue()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                return f"base64:{image_base64}"
        except Exception as e:
            logger.error(f"Image processing error for {file_path}: {str(e)}")
            raise ImageProcessingError(f"Failed to process image: {str(e)}")
