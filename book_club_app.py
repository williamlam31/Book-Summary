import requests
import time
import json
import subprocess
import os
import streamlit as st

st.set_page_config(page_title="Virtual Book Club", layout="wide")

def _mask_token(tok: str) -> str:
    if not tok:
        return "(missing)"
    tok = tok.strip()
    if len(tok) <= 10:
        return tok[:2] + "…" + tok[-2:]
    return tok[:4] + "…" + tok[-4:]


OPENLIB_SEARCH = "https://openlibrary.org/search.json"

HF_API_KEY = (st.secrets.get("hf_api_key") or st.secrets.get("hf_token") or os.environ.get("HF_API_KEY") or os.environ.get("HF_TOKEN") or "").strip()
HF_MODEL = (st.secrets.get("hf_model", "google/flan-t5-base") or "").strip().strip('"').strip("'")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

try:
    st.sidebar.caption(f"HF model: {HF_MODEL}")
    st.sidebar.caption(f"HF token: {_mask_token(HF_API_KEY)}")
except Exception:
    pass
# --------------------------------------------


FALLBACK_MODELS = [
    "google/gemma-2b-it",
    "HuggingFaceH4/zephyr-7b-beta",
    "tiiuae/falcon-7b-instruct",
]

def call_hf(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
    """
    Call the Hugging Face *serverless* Inference API for text-generation models.
    Includes a debug panel and clear error handling (404/loading/unexpected shapes).
    Will optionally fallback to a small set of public models if 404 is returned.
    """
    if not HF_API_KEY:
        st.error("No Hugging Face API key found in secrets (hf_api_key).")
        return ""
    if not HF_MODEL:
        st.error("No Hugging Face model set (hf_model).")
        return ""

    headers = {
        "x-wait-for-model": "true",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
        }
    }

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
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    for l in lines:
        while l and (l[0].isdigit() or l[0] in "-.)"):
            l = l[1:].lstrip()
        if l and l not in out:
            out.append(l)
        if len(out) == k:
            break
    return out

st.title("Virtual Book Club")

with st.sidebar:
    st.markdown("### Hugging Face API")
    if HF_API_KEY:
        st.success("API key found in secrets ✅")
    else:
        st.error("No `hf_api_key` found in Streamlit secrets.")
    st.caption(f"Model: {HF_MODEL or '(not set)'}")
    st.caption("Using Serverless Inference API")
    st.checkbox("Allow fallback to other models if 404", value=True, key="use_fallback_models")
    st.divider()
    if st.button("▶️ Test Hugging Face API"):
        test_text = call_hf("Say 'hello' in one short friendly sentence.", max_new_tokens=16, temperature=0.2)
        if test_text:
            st.success(f"HF OK: {test_text}")
        else:
            st.error("HF call returned empty. See the debug panel below for details.")

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
            st.write(summary or "No summary returned. Check the HF debug panel above.")

            st.markdown("**Discussion Questions**")
            if qs:
                for i, q in enumerate(qs, 1):
                    st.write(f"{i}. {q}")
            else:
                st.write("No questions returned. Check the HF debug panel above.")

        st.divider()
else:
    st.info("Search for books by genre, author, or title, then see AI summaries and questions.")
