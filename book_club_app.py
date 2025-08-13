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

GROQ_API_KEY = (st.secrets.get("groq_api_key") or os.environ.get("GROQ_API_KEY") or "").strip()
GROQ_MODEL = (st.secrets.get("groq_model", "llama3-70b-8192") or "").strip()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def call_llm(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
    if not GROQ_API_KEY:
        st.error("No Groq API key found in secrets (groq_api_key).")
        return ""
    if not GROQ_MODEL:
        st.error("No Groq model set (groq_model).")
        return ""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(max_new_tokens),
        "temperature": float(temperature),
    }

    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"Groq API call failed: {e}")
        return ""




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

            st.markdown("**Discussion Questions**")


        st.divider()
else:
    st.info("Search for books by genre, author, or title, then see AI summaries and questions.")
