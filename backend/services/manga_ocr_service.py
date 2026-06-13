from manga_ocr import MangaOcr

mocr = MangaOcr()

def extract_japanese_text(image):
    try:
        text = mocr(image)
        return text
    except Exception as e:
        print(f"OCR error: {e}")
        return ""
