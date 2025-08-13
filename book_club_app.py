import os
import time
import random
import requests
import streamlit as st

st.set_page_config(page_title="Virtual Book Club (Simple)", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"

def get_token():
    return (st.secrets.get("HUGGINGFACE_TOKEN", "") if hasattr(st, "secrets") else "") or os.getenv("HUGGINGFACE_TOKEN", "")

def call_hf(prompt, max_length=220):
    token = get_token()
    if not token:
        return ""
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/gpt2",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": prompt, "parameters": {"max_length": max_length, "temperature": 0.8, "do_sample": True, "top_p": 0.95}},
            timeout=25,
        )
        if r.ok and isinstance(r.json(), list) and r.json():
            text = r.json()[0].get("generated_text", "")
            if text.startswith(prompt):
                text = text[len(prompt):]
            return text.strip()
    except Exception:
        pass
    return ""

def fallback_text(prompt):
    return ""


    return ""

    title = "this book"
    if "'" in prompt:
        try:
            title = prompt.split("'")[1]
        except Exception:
            pass
    if "summary" in prompt.lower():
        return f"{title} offers a clear story with themes worth discussing. It mixes character moments and ideas in a way that invites reflection without being too complex."
    return f"Think about character growth, favorite scenes, main themes, and how {title} connects to your life."

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
        st.error("Could not fetch books right now.")
        return []

def cover_url(cover_id, size="M"):
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg" if cover_id else None

def fetch_openlib_description(work_key: str):
    """Fetch description text from Open Library Works API if available."""
    if not work_key:
        return ""
    try:
        url = f"https://openlibrary.org{work_key}.json"
        r = requests.get(url, timeout=8)
        if r.ok:
            data = r.json()
            desc = data.get('description', '')
            if isinstance(desc, dict):
                return desc.get('value', '') or ''
            if isinstance(desc, str):
                return desc
    except Exception:
        pass
    return ""

def make_summary(title, authors, subjects, work_key=None):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = f"Write a short, clear summary for '{title}' by {author_txt} about {topic_txt}. Summary:"
    text = call_hf(prompt, max_length=220)
    if text:
        return text.strip()
    # Fallback to Open Library description if HF returns nothing
    desc = fetch_openlib_description(work_key) if work_key else ""
    return desc.strip() if desc else ""

def make_questions(title, authors, subjects, k=5):
    """Generate discussion questions using Hugging Face only. No templates."""
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Generate {k} thoughtful book club discussion questions for the book "
        f"'{title}' by {author_txt}. Focus on {topic_txt}. "
        f"Return ONLY the questions as a numbered list 1-{k}, one per line, no extra commentary."
    )
    raw = call_hf(prompt, max_length=350)
    if not raw:
        return []

    import re as _re
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    qs = []
    for ln in lines:
        ln = _re.sub(r"^\s*\d+\s*[:\.).-]?\s*", "", ln)
        if ln and ln not in qs:
            qs.append(ln)
        if len(qs) == k:
            break
    if len(qs) < k and '?' in raw:
        parts = [p.strip()+'?' for p in raw.split('?') if p.strip()]
        for p in parts:
            if p not in qs:
                qs.append(p)
            if len(qs) == k:
                break
    return qs[:k]
