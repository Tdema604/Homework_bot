from PIL import Image
import pytesseract
from PIL import Image, ImageEnhance

image_path = 'path_to_your_image.jpg'
img = Image.open(image_path)

# Convert to grayscale
img = img.convert('L')

# Enhance contrast
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(2)

# Now pass this image to pytesseract
text = pytesseract.image_to_string(img, config='--oem 1')  # Try changing oem value to 1, 2, or 3.

# Path to tesseract on Windows (adjust if installed elsewhere)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Show result
print("🧠 OCR Result:")
print(text.strip())
