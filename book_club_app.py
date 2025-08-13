import requests
import streamlit as st

# ---------------- Basic Config ----------------
st.set_page_config(page_title="📚 Virtual Book Club (Q2)", page_icon="📚", layout="wide")

OPENLIB_SEARCH = "https://openlibrary.org/search.json"

# ---------------- Serverless Hugging Face Inference API ----------------
HF_API_KEY = st.secrets.get("hf_api_key", "")
# sanitize model id from secrets: trim spaces and stray quotes
HF_MODEL = (st.secrets.get("hf_model", "meta-llama/Meta-Llama-3-8B-Instruct") or "").strip().strip('"').strip("'")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

# Models to try automatically if the chosen model returns 404 on serverless HF Inference
FALLBACK_MODELS = [
    "google/flan-t5-base",
    "HuggingFaceH4/zephyr-7b-beta",
    "tiiuae/falcon-7b-instruct",
]

# ---------------- Helpers ----------------
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
        "Authorization": f"Bearer {HF_API_KEY}",
        # Ask serverless to wait for cold model start rather than returning 'loading'
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

    try:
        r = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

        # Debug panel
        with st.expander("Hugging Face API debug", expanded=False):
            st.code(f"Status: {r.status_code}\nURL: {HF_API_URL}", language="bash")
            try:
                text_preview = r.text[:2000] + ("..." if len(r.text) > 2000 else "")
                st.code(text_preview, language="json")
            except Exception:
                st.write("Non-text response.")

        # Specific 404 handling (common when model ID is wrong or token lacks access)
        if r.status_code == 404:
            # Try fallbacks automatically (if user allows it)
            use_fallback = st.session_state.get("use_fallback_models", True)
            if not use_fallback or not FALLBACK_MODELS:
                st.error(
                    f"HF 404: Model '{HF_MODEL}' not found or not accessible to this token. "
                    "Check the exact repo ID (case-sensitive), remove quotes/spaces in secrets, or accept the model’s terms."
                )
                return ""

            for fb in FALLBACK_MODELS:
                fb_url = f"https://api-inference.huggingface.co/models/{fb}"
                try:
                    rr = requests.post(fb_url, headers=headers, json=payload, timeout=60)
                    with st.expander("Hugging Face API debug (fallback)", expanded=False):
                        st.code(f"Status: {rr.status_code}\nURL: {fb_url}", language="bash")
                        try:
                            prev = rr.text[:2000] + ("..." if len(rr.text) > 2000 else "")
                            st.code(prev, language="json")
                        except Exception:
                            st.write("Non-text response.")
                    if rr.ok:
                        try:
                            data_fb = rr.json()
                            if isinstance(data_fb, list) and data_fb and isinstance(data_fb[0], dict):
                                st.warning(f"Primary model 404. Used fallback: {fb}")
                                return (data_fb[0].get("generated_text") or "").strip()
                            if isinstance(data_fb, dict) and "generated_text" in data_fb:
                                st.warning(f"Primary model 404. Used fallback: {fb}")
                                return (data_fb.get("generated_text") or "").strip()
                        except Exception:
                            pass
                except Exception as e:
                    st.write(f"Fallback request failed for {fb}: {e}")

            st.error(
                "All fallback models failed or returned unexpected responses. "
                "Consider deploying an Inference Endpoint for the chosen model or switching to a supported serverless model."
            )
            return ""

        if not r.ok:
            st.error(f"HF API HTTP error: {r.status_code}")
            # Try to show JSON error if available
            try:
                err = r.json()
                if isinstance(err, dict) and "error" in err:
                    st.error(f"HF error: {err.get('error')}")
            except Exception:
                pass
            return ""

        # Parse JSON
        try:
            data = r.json()
        except Exception as e:
            st.error(f"Failed to parse HF JSON: {e}")
            return ""

        # Handle common HF "loading" error
        if isinstance(data, dict) and "error" in data:
            msg = str(data.get("error"))
            if "loading" in msg.lower():
                st.warning("The HF model is loading. Please try again shortly or switch to a smaller model via secrets.")
            else:
                st.error(f"HF API error: {msg}")
            return ""

        # Typical text-generation shape
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return (data[0].get("generated_text") or "").strip()
        if isinstance(data, dict) and "generated_text" in data:
            return (data.get("generated_text") or "").strip()

        st.warning("HF API returned an unexpected shape. Check the debug panel for details.")
        return ""
    except Exception as e:
        st.error(f"Hugging Face request failed: {e}")
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
        while l and (l[0].isdigit() or l[0] in "-.)"):
            l = l[1:].lstrip()
        if l and l not in out:
            out.append(l)
        if len(out) == k:
            break
    return out

# ---------------- UI ----------------
st.title("📚 Virtual Book Club (Q2 — Serverless HF)")

with st.sidebar:
    st.markdown("### Hugging Face API (Serverless)")
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
