
import os
import time
import random
import requests
import streamlit as st

st.set_page_config(page_title="Virtual Book Club", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"


def get_ollama_host():
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")
def ollama_available():
    try:
        r = requests.get(f"{get_ollama_host()}/api/tags", timeout=4)
        return r.ok
    except Exception:
        return False

def call_ollama(prompt: str, model: str = None, options: dict = None, stream: bool = False) -> str:
  
    host = get_ollama_host()
    model = model or os.getenv("OLLAMA_MODEL", "llama3:latest")
    payload = {"model": model, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    try:
        r = requests.post(f"{host}/api/generate", json=payload, timeout=30)
        if not r.ok:
            return ""
        data = r.json()
        return (data.get("response") or "").strip()
    except Exception:
        return ""
def search_books(genre=None, author=None, title=None, limit=5):
    params = {
        "limit": limit,
        "has_fulltext": "true",
        "fields": "key,title,author_name,first_publish_year,subject,isbn,cover_i,ratings_average,ratings_count",
    }
    q = []
    if title:  q.append(f'title:"{title.strip()}"')
    if author: q.append(f'author:"{author.strip()}"')
    if genre and genre != "Any Genre":
        mapping = {"Science Fiction": "science fiction", "Self-Help": "self help"}
        q.append(f'subject:"{mapping.get(genre, genre.lower())}"')
    params["q"] = " AND ".join(q) if q else "fiction"
    try:
        r = requests.get(OPENLIB_SEARCH, params=params, timeout=10)
        r.raise_for_status()
        out = []
        for d in r.json().get("docs", []):
            if d.get("title") and d.get("author_name"):
                out.append({
                    "title": d["title"],
                    "authors": d["author_name"],
                    "year": d.get("first_publish_year"),
                    "subjects": (d.get("subject") or [])[:5],
                    "cover_id": d.get("cover_i"),
                    "rating": d.get("ratings_average"),
                    "rating_count": d.get("ratings_count", 0),
                })
        return out
    except Exception:
        return []

def cover_url(cover_id, size="M"):
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg" if cover_id else None

def make_summary(title, authors, subjects, model=None):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = f"Write a short, clear summary for '{title}' by {author_txt} about {topic_txt}. Summary:"
    options = {"temperature": 0.7}
    return call_ollama(prompt, model=model, options=options)
def make_questions(title, authors, subjects, k=5, model=None):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Generate {k} thoughtful book club discussion questions for the book "
        f"'{title}' by {author_txt}. Focus on {topic_txt}. "
        f"Return ONLY the questions as a numbered list 1-{k}, one per line, no extra commentary."
    )
    raw = call_ollama(prompt, model=model, options={"temperature": 0.7})
    if not raw:
        return []
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    qs = []
    import re as _re
    for ln in lines:
        ln = _re.sub(r"^\s*\d+\s*[:\).\-]?\s*", "", ln)
        if ln and ln not in qs:
            qs.append(ln)
        if len(qs) == k:
            break
    if len(qs) < k and "?" in raw:
        parts = [p.strip()+"?" for p in raw.split("?") if p.strip()]
        for p in parts:
            if p not in qs:
                qs.append(p)
            if len(qs) == k:
                break
    return qs[:k]
