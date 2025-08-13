
import os
import time
import random
import requests
import streamlit as st

st.set_page_config(page_title="Virtual Book Club — AI Only (Debug)", page_icon="📚", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"


def get_token():
    return (st.secrets.get("HUGGINGFACE_TOKEN", "") if hasattr(st, "secrets") else "") or os.getenv("HUGGINGFACE_TOKEN", "")

def call_hf(prompt: str, max_length: int = 220, model: str = "gpt2") -> str:
    token = get_token()
    if not token:
        return ""
    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
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

def make_summary(title, authors, subjects, model="gpt2"):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = f"Write a short, clear summary for '{title}' by {author_txt} about {topic_txt}. Summary:"
    return call_hf(prompt, max_length=220, model=model)

def make_questions(title, authors, subjects, k=5, model="gpt2"):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Generate {k} thoughtful book club discussion questions for the book "
        f"'{title}' by {author_txt}. Focus on {topic_txt}. "
        f"Return ONLY the questions as a numbered list 1-{k}, one per line, no extra commentary."
    )
    raw = call_hf(prompt, max_length=350, model=model)
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

st.title("📚 Virtual Book Club — AI Only (Debug)")


_hf = bool(get_token())
if _hf:
    st.caption("✨ Hugging Face enabled. Summaries & questions are AI generated.")
else:
    st.warning("ℹ️ No HUGGINGFACE_TOKEN found in secrets or environment. The app will show empty summaries/questions.")


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
                url = cover_url(book["cover_id"])
                if url:
                    st.image(url, width=130)
                st.markdown(f"**{book['title']}** — *{', '.join(book['authors'][:2])}*")
                if book.get("year"): st.write(f"📅 {book['year']}")
                if book.get("rating"): st.write(f"⭐ {book['rating']:.1f}/5 ({book['rating_count']} ratings)")
                if book.get("subjects"): st.write(", ".join(book["subjects"][:3]))
            with right:
                key = f"{book['title']}|{book['authors'][0] if book['authors'] else 'Unknown'}|{book.get('year')}|{book.get('cover_id')}"
                if key not in st.session_state["ai_cache"]:
                    with st.spinner("Generating with Hugging Face..."):
                        time.sleep(0.05)
                        summary = make_summary(book["title"], book["authors"], book["subjects"])
                        questions = make_questions(book["title"], book["authors"], book["subjects"], k=5)
                        st.session_state["ai_cache"][key] = (summary, questions)
                summary, questions = st.session_state["ai_cache"][key]

                st.subheader("Summary")
                if summary:
                    st.write(summary)
                else:
                    st.info("No summary returned by the model. Check your token or try again.")

                st.subheader("Discussion Questions")
                if questions:
                    for i, q in enumerate(questions, 1):
                        st.write(f"{i}. {q}")
                else:
                    st.info("No questions returned by the model.")

            st.divider()
