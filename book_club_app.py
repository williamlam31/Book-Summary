import os
import re
import time
import requests
import streamlit as st

# === Hugging Face (Option A) Summarization & Question Generation ===
try:
    from transformers import pipeline
    HF_SUMMARIZER_MODEL = "facebook/bart-large-cnn"
    summarizer = pipeline("summarization", model=HF_SUMMARIZER_MODEL)

    HF_QG_MODEL = "google/flan-t5-base"
    qg = pipeline("text2text-generation", model=HF_QG_MODEL)
except Exception as _hf_exc:
    # If transformers isn't available, downstream calls will surface the error in UI
    summarizer = None
    qg = None

def _book_context(title, authors, subjects):
    authors = authors or []
    subjects = subjects or []
    author_txt = ", ".join(authors[:2]) if isinstance(authors, list) else str(authors)
    topic_txt = ", ".join(subjects[:5]) if isinstance(subjects, list) else str(subjects)
    return f"Title: {title}\\nAuthor(s): {author_txt or 'Unknown'}\\nTopics: {topic_txt or 'general themes'}"

def hf_summarize(text: str) -> str:
    if not text:
        return ""
    if summarizer is None:
        return "(Transformers not installed)"
    out = summarizer(text, max_length=220, min_length=60, do_sample=False)
    return (out[0].get("summary_text","") or "").strip()

def hf_generate_questions(context: str, k: int = 5):
    if not context:
        return []
    if qg is None:
        return ["(Transformers not installed)"]
    prompt = (
        "Generate {k} thoughtful book club questions based on this text. "
        "Return only a numbered list:\\n\\n{context}\\n\\nQuestions:"
    ).format(k=k, context=str(context)[:3000])
    out = qg(prompt, max_new_tokens=256, do_sample=False)
    raw = out[0].get("generated_text","").strip()

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    qs = []
    import re as _re
    for ln in lines:
        ln = _re.sub(r"^\\s*\\d+\\s*[:\\.).-]?\\s*", "", ln)
        if ln.endswith("?") and ln not in qs:
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
# === End Hugging Face block ===

st.set_page_config(page_title="📚 Virtual Book Club — Ollama (Debug)", page_icon="📚", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"

# -------------------- config helpers --------------------
def _secrets_get(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def get_ollama_host() -> str:
    # Prefer Secrets, then env var, then local default
    return _secrets_get("OLLAMA_HOST", os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")

def get_ollama_model() -> str:
    # DEFAULT CHANGED HERE → "gpt-oss"
    return _secrets_get("OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "gpt-oss"))

def get_ollama_headers() -> dict:
    """
    Optional API key support (if your proxy requires it).
    Defaults to sending Authorization: Bearer <key>.
    You can override the header name in the Diagnostics panel.
    """
    ov = st.session_state.get("OVERRIDES", {})
    key = ov.get("API_KEY") or _secrets_get("OLLAMA_API_KEY", os.getenv("OLLAMA_API_KEY", ""))
    header_name = ov.get("AUTH_HEADER") or "Authorization"
    return ({header_name: f"Bearer {key}"} if key else {})

def ollama_available(timeout=3.0) -> (bool, str):
    """Quick ping to check if Ollama responds; return (ok, message)."""
    host = get_ollama_host()
    try:
        r = requests.get(f"{host}/api/tags", headers=get_ollama_headers(), timeout=timeout)
        if r.ok:
            return True, f"OK via /api/tags ({host})"
        return False, f"{r.status_code} from {host}/api/tags"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def call_ollama(prompt: str):
    """
    (Stub) Ollama disabled. Using Hugging Face instead.
    """
    return "(Ollama disabled in this build)"


def cover_url(cover_id, size="M"):
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg" if cover_id else None

def make_summary(title, authors, subjects):
    """
    Replaced to use Hugging Face summarizer.
    """
    context = _book_context(title, authors, subjects)
    return hf_summarize(context)


def make_questions(title, authors, subjects, k=5):
    """
    Replaced to use Hugging Face question generator.
    """
    context = _book_context(title, authors, subjects)
    return hf_generate_questions(context, k=k)
