import os
import re
import json
import time
import hashlib
import nltk
import fitz  # PyMuPDF
import numpy as np
from typing import Optional
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from google import genai

nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)


# ─── TEXT EXTRACTION ─────────────────────────────────────────────────────────

def _configure_tesseract_if_provided() -> None:
    """Optionally set pytesseract command path via env var.

    On Windows, users often need to install Tesseract and set the full path.
    We support an env var `TESSERACT_CMD` to avoid hardcoding a machine-specific path.
    """
    try:
        import pytesseract

        tcmd = os.getenv('TESSERACT_CMD', '').strip()
        if tcmd:
            pytesseract.pytesseract.tesseract_cmd = tcmd
    except Exception:
        return


def _ocr_pil_image(img, *, psm: int = 6) -> str:
    """Run OCR on a PIL image with light preprocessing."""
    try:
        import pytesseract
        from PIL import ImageOps, ImageEnhance

        _configure_tesseract_if_provided()

        # Basic preprocessing that generally helps typed/scanned text.
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(1.8)
        gray = ImageEnhance.Sharpness(gray).enhance(1.3)

        # Simple thresholding to reduce background noise.
        bw = gray.point(lambda p: 255 if p > 160 else 0)

        config = f"--oem 3 --psm {psm}"
        text = pytesseract.image_to_string(bw, config=config)
        return (text or '').strip()
    except Exception as e:
        print(f"OCR error: {e}")
        return ''


def _pdf_ocr_fallback(file_path: str, *, zoom: float = 2.5, max_pages: int = 8) -> str:
    """OCR a scanned PDF by rendering pages to images and running Tesseract.

    - `zoom` controls render resolution (higher -> better OCR, slower).
    - `max_pages` avoids runaway CPU on large PDFs.
    """
    try:
        from PIL import Image
    except Exception:
        return ''

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"PDF open error for OCR: {e}")
        return ''

    texts = []
    try:
        page_count = min(len(doc), max_pages)
        matrix = fitz.Matrix(zoom, zoom)
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            mode = 'RGB'
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            page_text = _ocr_pil_image(img, psm=6)
            if page_text:
                texts.append(page_text)
    except Exception as e:
        print(f"PDF OCR render error for {file_path}: {e}")
    finally:
        try:
            doc.close()
        except Exception:
            pass

    return "\n\n".join(texts).strip()

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            text = ''.join(page.get_text() for page in doc)
            doc.close()
            text = (text or '').strip()
            # If it's a scanned PDF, text extraction is often empty; fall back to OCR.
            if len(text) < 50:
                ocr_text = _pdf_ocr_fallback(file_path)
                return (ocr_text or text).strip()
            return text
        elif ext == '.docx':
            doc = Document(file_path)
            return ' '.join(p.text for p in doc.paragraphs).strip()
        elif ext in {'.png', '.jpg', '.jpeg'}:
            # Optional OCR: requires Pillow + pytesseract (+ Tesseract installed on the OS)
            try:
                from PIL import Image
                img = Image.open(file_path)
                return _ocr_pil_image(img, psm=6)
            except Exception as e:
                print(f"OCR error for {file_path}: {e}")
                return ''
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read().strip()
    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
    return ''


# ─── TEXT PREPROCESSING ──────────────────────────────────────────────────────

def preprocess_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\S*@\S*\s?', '', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── PLAGIARISM SCORE ────────────────────────────────────────────────────────

def plagiarism_score(text1: str, text2: str):
    t1 = preprocess_text(text1)
    t2 = preprocess_text(text2)
    if not t1 or not t2:
        return 0.0, 0.0

    # 1. Global Plagiarism Score
    try:
        vectorizer = TfidfVectorizer()
        vec_global = vectorizer.fit_transform([t1, t2])
        sim_global = cosine_similarity(vec_global[0:1], vec_global[1:2])[0][0]
        sim_pct = round(sim_global * 100, 2)
    except ValueError:
        return 0.0, 0.0

    # 2. Chunking for Confidence Score via Standard Deviation
    from nltk.tokenize import sent_tokenize
    try:
        chunks = sent_tokenize(text1)
    except Exception:
        chunks = text1.split('.')

    chunks = [preprocess_text(c) for c in chunks if len(c.strip()) > 10]
    
    if not chunks:
        # Fallback if text is too short to chunk
        return sim_pct, 50.0

    try:
        vec_ref = TfidfVectorizer().fit([t2])
        ref_matrix = vec_ref.transform([t2])
        chunk_matrices = vec_ref.transform(chunks)
        chunk_sims = cosine_similarity(chunk_matrices, ref_matrix).flatten()
        
        # Calculate standard deviation of chunk similarities
        std_dev = np.std(chunk_sims)
        
        # Calculate confidence using std dev (Lower std dev => higher confidence in consistency)
        # We cap it at 100, subtracting std_dev impact. If std_dev is 0, confidence is 100%. 
        # Since similarities are 0-1, std_dev is usually 0 to ~0.5
        conf = max(0.0, min(100.0, round(100 * (1.0 - std_dev), 2)))
        
        if sim_pct == 100.0:
            conf = 100.0
            
    except ValueError:
        conf = 50.0

    return sim_pct, conf


# ─── QUALITY SCORE ───────────────────────────────────────────────────────────

def quality_score(text: str) -> float:
    """Score 0-100 based on length, vocabulary richness, and sentence structure."""
    try:
        from nltk.tokenize import word_tokenize, sent_tokenize
        words = word_tokenize(text.lower())
        sentences = sent_tokenize(text)
    except Exception:
        words = text.lower().split()
        sentences = text.split('.')

    if not words:
        return 0.0

    unique_ratio = len(set(words)) / len(words)
    word_count_score = min(40, len(words) * 0.1)
    sentence_score = min(30, len(sentences) * 2)
    vocab_score = unique_ratio * 30

    return round(min(100, word_count_score + sentence_score + vocab_score), 1)


# ─── GEMINI API ──────────────────────────────────────────────────────────────

def gemini_generate(prompt: str) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "Gemini API key not configured. Please add GEMINI_API_KEY to your .env file."
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ─── AI SOLUTION GENERATION ──────────────────────────────────────────────────

def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def cached_solution_path(assignment_text: str) -> str:
    h = _hash_text(assignment_text)[:16]
    dirpath = os.path.join(settings.MEDIA_ROOT, 'generated_solutions')
    os.makedirs(dirpath, exist_ok=True)
    return os.path.join(dirpath, f'solution_{h}.txt')


def generate_solution_with_ai(assignment_text: str) -> str:
    cache_path = cached_solution_path(assignment_text)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    prompt = (
        "You are a helpful academic assistant. Write a clear, correct, and well-structured solution "
        "to the following assignment. Include step-by-step reasoning, relevant examples, and academic "
        "language. Format with clear sections.\n\n"
        f"Assignment:\n{assignment_text}"
    )
    result = gemini_generate(prompt)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(result)
    return result


# ─── AI FEEDBACK GENERATION ──────────────────────────────────────────────────

def generate_feedback_with_ai(assignment_text: str, student_submission: str, plagiarism_pct: float, quality_pct: float) -> str:
    prompt = (
        f"You are an academic evaluator. Review this student's assignment submission.\n\n"
        f"ASSIGNMENT:\n{assignment_text[:1000]}\n\n"
        f"STUDENT SUBMISSION:\n{student_submission[:2000]}\n\n"
        f"METRICS:\n- Plagiarism Score: {plagiarism_pct}%\n- Quality Score: {quality_pct}/100\n\n"
        "Provide constructive feedback in 3-4 sentences covering: content relevance, areas for improvement, "
        "and whether the submission demonstrates understanding. Be encouraging but honest."
    )
    return gemini_generate(prompt)
