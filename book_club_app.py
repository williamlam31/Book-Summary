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



def call_hf(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
  
    if not HF_API_KEY:
        st.error("No Hugging Face API key found in secrets (hf_api_key).")
        return ""
    if not HF_MODEL:
        st.error("No Hugging Face model set (hf_model).")
        return ""


        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": int(max_new_tokens),
                "temperature": float(temperature),
                "return_full_text": False,
            }
        


OPENAI_API_KEY = (st.secrets.get("openai_api_key") or os.environ.get("OPENAI_API_KEY") or "").strip()
CHATGPT_MODEL = (st.secrets.get("openai_model", "gpt-4o-mini") or "gpt-4o-mini").strip()

def _mask_token(tok: str) -> str:
    if not tok:
        return "(missing)"
    tok = tok.strip()
    if len(tok) <= 10:
        return tok[:2] + "…" + tok[-2:]
    return tok[:4] + "…" + tok[-4:]

def call_chatgpt(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
    """
    Call OpenAI Chat Completions API with a concise system prompt.
    Returns a string ("" on error) and shows friendly errors in Streamlit.
    """
    if not OPENAI_API_KEY:
        st.error("No OpenAI API key found. Set 'openai_api_key' in Streamlit secrets or OPENAI_API_KEY env.")
        return ""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": CHATGPT_MODEL,
        "temperature": float(temperature),
        "max_tokens": int(max_new_tokens),
        "messages": [
            {"role": "system", "content": "You are a concise, friendly assistant for a virtual book club. Keep answers short and helpful."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        import requests
        r = requests.post(url, headers=headers, json=body, timeout=60)
        # Surface quota / auth issues clearly
        if r.status_code == 401:
            st.error("OpenAI auth failed (401). Check your API key.")
            return ""
        if r.status_code == 429:
            st.warning("Rate limited by OpenAI (429). Please try again shortly.")
            return ""
        r.raise_for_status()
        data = r.json()
        # Expected format
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return (content or "").strip()
    except Exception as e:
        st.error(f"OpenAI request failed: {e}")
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
    return call_chatgpt(prompt)

def make_questions(title, authors, subjects, k=5):
    author_txt = ", ".join(authors[:2]) if authors else "Unknown"
    topic_txt = ", ".join(subjects[:3]) if subjects else "general themes"
    prompt = (
        f"Create {k} concise book club discussion questions about '{title}' by {author_txt}. "
        f"Consider these topics: {topic_txt}. "
        f"Return only a numbered list 1-{k}, one per line."
    )
    text = call_chatgpt(prompt)
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

with st.expander("⚙️ Debug (LLM & API)", expanded=False):
    st.write({
        "OPENAI_MODEL": CHATGPT_MODEL,
        "OPENAI_API_KEY_present": bool(OPENAI_API_KEY),
        "OPENAI_API_KEY_masked": _mask_token(OPENAI_API_KEY),
    })
    if st.button("🔬 Test ChatGPT (The Hobbit)"):
        sample = call_chatgpt("Summarize 'The Hobbit' in 2 sentences.", max_new_tokens=80, temperature=0.3)
        st.write(sample or "(no output)")


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
            if b.get("subjects"):
                st.write(", ".join(b["subjects"][:3]))

        with right:
            with st.spinner("Generating summary and questions..."):
                summary = make_summary(b["title"], b["authors"], b["subjects"])
                qs = make_questions(b["title"], b["authors"], b["subjects"], k=5)

            st.markdown("**Summary**")
            st.write(summary or "No summary returned.")

            st.markdown("**Discussion Questions**")
            if qs:
                for i, q in enumerate(qs, 1):
                    st.write(f"{i}. {q}")
            else:
                st.write("No questions returned.")


        st.divider()
else:
    st.info("Search for books by genre, author, or title, then see AI summaries and questions.")
