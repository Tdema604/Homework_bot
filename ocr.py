# ocr.py
import pytesseract
from PIL import Image

def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using Tesseract OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""
