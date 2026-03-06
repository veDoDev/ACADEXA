import os
import re
import json
import time
import hashlib
import nltk
import fitz  # PyMuPDF
import numpy as np
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from google import genai

nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)


# ─── TEXT EXTRACTION ─────────────────────────────────────────────────────────

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            text = ''.join(page.get_text() for page in doc)
            doc.close()
            return text.strip()
        elif ext == '.docx':
            doc = Document(file_path)
            return ' '.join(p.text for p in doc.paragraphs).strip()
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
    vectorizer = TfidfVectorizer().fit_transform([t1, t2])
    sim = cosine_similarity(vectorizer[0:1], vectorizer[1:2])[0][0]
    sim_pct = round(sim * 100, 2)

    arr = vectorizer.toarray()
    mean, std = np.mean(arr), np.std(arr)
    if sim_pct == 100.0:
        conf = 100.0
    else:
        conf = max(0, min(100, round((mean / (std + 1e-6)) * sim_pct, 2)))
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
