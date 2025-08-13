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
            return text.strip() or fallback_text(prompt)
    except Exception:
        pass
    return fallback_text(prompt)

def fallback_text(prompt):
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
    base = [
        f"What stood out most to you in '{title}' and why?",
        f"How do the characters in '{title}' change over time?",
        f"Which theme in '{title}' felt most relevant today?",
        f"Did anything in '{title}' challenge your views?",
        f"How would you describe {', '.join(authors[:1]) if authors else 'the author'}'s style in one sentence?",
        f"If you could ask the author one question about '{title}', what would it be?",
    ]
    for s in (subjects or [])[:2]:
        base.append(f"How does '{title}' handle the topic of {s}?")
    random.shuffle(base)
    return base[:k]

st.title("📚 Virtual Book Club (Simple)")

st.header("Find Your Book(s)")
row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    genre = st.selectbox(
        "Genre:",
        ["Any Genre", "Fiction", "Mystery", "Romance", "Science Fiction", "Fantasy", "Biography", "History", "Self-Help", "Business", "Philosophy", "Psychology", "Poetry", "Horror", "Thriller", "Adventure"]
    )
with row1_col2:
    book_limit = st.selectbox("Number of Results:", list(range(1, 11)), index=4)

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    author = st.text_input("Author (optional)")
with row2_col2:
    title = st.text_input("Book Title (optional)")

if st.button("🔍 Search"):
    with st.spinner("Searching..."):
        books = search_books(genre if genre != "Any Genre" else None, author.strip() or None, title.strip() or None, book_limit)
        st.session_state.books = books
        st.session_state.search_performed = True


if "ai_cache" not in st.session_state:
    st.session_state.ai_cache = {}

if st.session_state.get("search_performed") and st.session_state.get("books"):
    st.subheader(f"Found {len(st.session_state.books)} book(s)")
    for book in st.session_state.books:
        left, right = st.columns([1, 2], vertical_alignment="top")
        with left:
            url = cover_url(book["cover_id"])
            if url:
                st.image(url, width=130)
            st.markdown(f"**{book['title']}** — *{', '.join(book['authors'][:2])}*")
            if book.get("year"): st.write(f"📅 {book['year']}")
            if book.get("rating"): st.write(f"⭐ {book['rating']:.1f}/5 ({book['rating_count']} ratings)")
            if book["subjects"]: st.write(", ".join(book["subjects"][:3]))

        with right:
            key = f"{book['title']}|{book['authors'][0] if book['authors'] else 'Unknown'}|{book.get('year')}|{book.get('cover_id')}"
            if key not in st.session_state.ai_cache:
                with st.spinner("Thinking..."):
                    time.sleep(0.05)
                    s = make_summary(book["title"], book["authors"], book["subjects"], work_key=book.get("work_key"))
                    q = make_questions(book["title"], book["authors"], book["subjects"], k=5)
                    st.session_state.ai_cache[key] = (s, q)

            summary, questions = st.session_state.ai_cache[key]
            st.subheader("Summary")
            if summary:
                st.write(summary)
            else:
                st.info("No summary available from Open Library or AI for this title.")

            st.subheader("Discussion Questions")
            for i, q in enumerate(questions, 1):
                st.write(f"{i}. {q}")

        st.divider()
