
import requests
import streamlit as st

# ---------------- Basic Config ----------------
st.set_page_config(page_title="📚 Virtual Book Club (Q2)", page_icon="📚", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"

# Hugging Face API config (strictly HTTP API)
HF_API_KEY = st.secrets.get("hf_api_key", "")
HF_MODEL = st.secrets.get("hf_model", "meta-llama/Meta-Llama-3-8B-Instruct")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

# ---------------- Helpers ----------------
def call_hf(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
    """
    Minimal call to Hugging Face Inference API using requests.
    Expects a text-generation capable model. Returns empty string on failure.
    """
    if not HF_API_KEY:
        return ""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
        }
    }
    try:
        r = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        if not r.ok:
            return ""
        data = r.json()
        # Handle common HF response shapes
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Classic text-generation pipeline shape
            return (data[0].get("generated_text") or "").strip()
        if isinstance(data, dict) and "generated_text" in data:
            return (data.get("generated_text") or "").strip()
        if isinstance(data, dict) and "error" in data:
            return ""
    except Exception:
        pass
    return ""

def search_books(genre=None, author=None, title=None, limit=5):
    params = {"limit": limit, "has_fulltext": "true"}
    q_parts = []
    if title:
        q_parts.append(f'title:"{title.strip()}"')
    if author:
        q_parts.append(f'author:"{author.strip()}"')
    if genre and genre != "Any Genre":
        q_parts.append(f'subject:"{genre.lower()}"')
    params["q"] = " AND ".join(q_parts) if q_parts else "fiction"
    try:
        r = requests.get(OPENLIB_SEARCH, params=params, timeout=20)
        r.raise_for_status()
        docs = r.json().get("docs", [])
    except Exception:
        docs = []

    books = []
    for d in docs[:limit]:
        t = d.get("title")
        a = d.get("author_name") or []
        if not t or not a:
            continue
        books.append({
            "title": t,
            "authors": a,
            "year": d.get("first_publish_year"),
            "subjects": (d.get("subject") or [])[:5],
            "cover_id": d.get("cover_i"),
        })
    return books

def cover_url(cover_id, size="M"):
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg" if cover_id else None

def make_summary(title, authors, subjects):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Write a short, friendly summary of the book '{title}' by {author_txt}. "
        f"Focus on: {topic_txt}. Keep it under 100 words."
    )
    return call_hf(prompt)

def make_questions(title, authors, subjects, k=5):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Create {k} concise book club discussion questions about '{title}' by {author_txt}. "
        f"Consider these topics: {topic_txt}. "
        f"Return only a numbered list 1-{k}, one per line."
    )
    text = call_hf(prompt)
    if not text:
        return []
    # Simple parse to strip numbering/bullets
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    for l in lines:
        # remove any leading numbers/bullets
        while l and (l[0].isdigit() or l[0] in "-.)"):
            l = l[1:].lstrip()
        if l and l not in out:
            out.append(l)
        if len(out) == k:
            break
    return out

# ---------------- UI ----------------
st.title("📚 Virtual Book Club (Q2 — Simple)")

with st.sidebar:
    st.markdown("### Hugging Face API")
    if HF_API_KEY:
        st.success("API key found in secrets ✅")
    else:
        st.error("No `hf_api_key` found in Streamlit secrets.")
    st.caption(f"Model: {HF_MODEL}")

st.header("Find Books")
c1, c2 = st.columns(2)
with c1:
    genre = st.selectbox(
        "Genre",
        ["Any Genre", "Fiction", "Mystery", "Romance", "Science Fiction", "Fantasy",
         "Biography", "History", "Self-Help", "Business", "Philosophy", "Psychology",
         "Poetry", "Horror", "Thriller", "Adventure"],
        index=0,
    )
with c2:
    limit = st.slider("Number of results", 1, 8, 5)

c3, c4 = st.columns(2)
with c3:
    author = st.text_input("Author (optional)")
with c4:
    title = st.text_input("Title (optional)")

if st.button("🔍 Search"):
    st.session_state["books"] = search_books(
        genre if genre != "Any Genre" else None,
        author.strip() or None,
        title.strip() or None,
        limit,
    )

books = st.session_state.get("books", [])
if books:
    st.subheader(f"Found {len(books)} book(s)")
    for b in books:
        left, right = st.columns([1, 2])
        with left:
            if b.get("cover_id"):
                st.image(cover_url(b["cover_id"]), width=130)
            st.markdown(f"**{b['title']}**")
            st.caption(", ".join(b["authors"][:2]))
            if b.get("year"):
                st.write(f"📅 {b['year']}")
            if b.get("subjects"):
                st.write(", ".join(b["subjects"][:3]))

        with right:
            with st.spinner("Generating summary and questions..."):
                summary = make_summary(b["title"], b["authors"], b["subjects"])
                qs = make_questions(b["title"], b["authors"], b["subjects"], k=5)

            st.markdown("**Summary**")
            st.write(summary or "No summary returned (check API key/model).")

            st.markdown("**Discussion Questions**")
            if qs:
                for i, q in enumerate(qs, 1):
                    st.write(f"{i}. {q}")
            else:
                st.write("No questions returned (check API key/model).")

        st.divider()
else:
    st.info("Search for books by genre, author, or title, then see AI summaries and questions.")
