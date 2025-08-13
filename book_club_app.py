
import os
import time
import requests
import streamlit as st

st.set_page_config(page_title="📚 Virtual Book Club — Ollama (Debug)", page_icon="📚", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"

# -------------------- config helpers --------------------
def _secrets_get(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def get_ollama_host() -> str:
    # Prefer Streamlit secrets, then env var, then local default
    return _secrets_get("OLLAMA_HOST", os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")

def get_ollama_model() -> str:
    return _secrets_get("OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "llama3:latest"))

def get_ollama_headers() -> dict:
    # Optional API key (if your gateway expects it). Sends as Bearer by default.
    key = _secrets_get("OLLAMA_API_KEY", os.getenv("OLLAMA_API_KEY", ""))
    return {"Authorization": f"Bearer {key}"} if key else {}

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

def call_ollama(prompt: str, model: str = None, options: dict = None, timeout=8.0) -> str:
    """Call Ollama /api/generate with short timeout; return '' on failure."""
    host = get_ollama_host()
    model = model or get_ollama_model()
    payload = {"model": model, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    try:
        r = requests.post(f"{host}/api/generate", json=payload, headers=get_ollama_headers(), timeout=timeout)
        if not r.ok:
            return ""
        data = r.json()
        return (data.get("response") or "").strip()
    except Exception:
        return ""

# -------------------- data helpers --------------------
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
                    "work_key": d.get("key"),
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
    return call_ollama(prompt, model=model or get_ollama_model(), options={"temperature": 0.7})

def make_questions(title, authors, subjects, k=5, model=None):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Generate {k} thoughtful book club discussion questions for the book "
        f"'{title}' by {author_txt}. Focus on {topic_txt}. "
        f"Return ONLY the questions as a numbered list 1-{k}, one per line, no extra commentary."
    )
    raw = call_ollama(prompt, model=model or get_ollama_model(), options={"temperature": 0.7})
    if not raw:
        return []
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    qs = []
    import re as _re
    for ln in lines:
        ln = _re.sub(r"^\s*\d+\s*[:\.).-]?\s*", "", ln)
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

# -------------------- UI --------------------
st.title("📚 Virtual Book Club — Ollama (Debug)")

with st.expander("Diagnostics", expanded=True):
    host = get_ollama_host()
    model = get_ollama_model()
    ok, msg = ollama_available(timeout=2.5)
    st.markdown(f"**Host:** `{host}`")
    st.markdown(f"**Model:** `{model}`")
    st.markdown(f"**Connectivity:** {('✅ ' if ok else '❌ ')+ msg}")
    st.caption("Tip: On Streamlit Cloud, `http://localhost:11434` will not work. Point `OLLAMA_HOST` to a public server running Ollama, e.g. `http://<your-server-ip>:11434`.")

    if st.button("🔎 Quick test (Ask model to say 'OK')"):
        resp = call_ollama("Respond with only the word: OK", model=model, options={"temperature": 0.1}, timeout=6.0)
        st.write("Response:", resp or "(no response)")

# Search controls
st.header("Find Your Book(s)")
c1, c2 = st.columns(2)
with c1:
    genre = st.selectbox(
        "Genre:",
        ["Any Genre", "Fiction", "Mystery", "Romance", "Science Fiction", "Fantasy", "Biography", "History", "Self-Help", "Business", "Philosophy", "Psychology", "Poetry", "Horror", "Thriller", "Adventure"],
    )
with c2:
    book_limit = st.selectbox("Number of Results:", list(range(1, 11)), index=4)

c3, c4 = st.columns(2)
with c3:
    author = st.text_input("Author (optional)")
with c4:
    title = st.text_input("Book Title (optional)")

if st.button("🔍 Search"):
    with st.spinner("Searching..."):
        books = search_books(genre if genre != "Any Genre" else None, author.strip() or None, title.strip() or None, book_limit)
        st.session_state["books"] = books
        st.session_state["search_performed"] = True

if "ai_cache" not in st.session_state:
    st.session_state["ai_cache"] = {}

if st.session_state.get("search_performed"):
    books = st.session_state.get("books", [])
    if not books:
        st.warning("No books found. Try broadening your search.")
    else:
        st.subheader(f"Found {len(books)} book(s)")
        for book in books:
            left, right = st.columns([1, 2], vertical_alignment="top")
            with left:
                url = cover_url(book.get("cover_id"))
                if url:
                    st.image(url, width=130)
                st.markdown(f"**{book['title']}** — *{', '.join(book['authors'][:2])}*")
                if book.get("year"): st.write(f"📅 {book['year']}")
                if book.get("rating"): st.write(f"⭐ {book['rating']:.1f}/5 ({book['rating_count']} ratings)")
                if book.get("subjects"): st.write(", ".join(book["subjects"][:3]))
            with right:
                key = f"{book['title']}|{book['authors'][0] if book['authors'] else 'Unknown'}|{book.get('year')}|{book.get('cover_id')}"
                if key not in st.session_state["ai_cache"]:
                    with st.spinner("🧠 Generating with Ollama..."):
                        time.sleep(0.05)
                        summary = make_summary(book["title"], book["authors"], book["subjects"], model=get_ollama_model())
                        questions = make_questions(book["title"], book["authors"], book["subjects"], k=5, model=get_ollama_model())
                        st.session_state["ai_cache"][key] = (summary, questions)
                summary, questions = st.session_state["ai_cache"][key]

                st.subheader("🤖 Summary")
                if summary:
                    st.write(summary)
                else:
                    st.info("No summary returned. Check Diagnostics above.")

                st.subheader("💬 Discussion Questions")
                if questions:
                    for i, q in enumerate(questions, 1):
                        st.write(f"{i}. {q}")
                else:
                    st.info("No questions returned.")

            st.divider()
