import streamlit as st
import requests
import json
import time
import random
from typing import Dict, List, Optional
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Virtual Book Club",
    page_icon="📚",
    layout="wide"
)


st.markdown("""
<style>
.book-card {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 10px;
    margin: 10px 0;
    border-left: 5px solid #4CAF50;
}

.discussion-section {
    background-color: #e8f4fd;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.genre-tag {
    display: inline-block;
    background-color: #4CAF50;
    color: white;
    padding: 5px 10px;
    border-radius: 15px;
    margin: 2px;
    font-size: 12px;
}

.search-info {
    background-color: #d1ecf1;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    border-left: 4px solid #bee5eb;
}

/* Comprehensive removal of all white bars and containers */
.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* Target all potential container elements */
.stMarkdown {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
}

div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
}

.element-container {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
}

/* Remove all button spacing and backgrounds */
.stButton {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
}

div[data-testid="stButton"] {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
}

.stButton > button {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
}

/* Remove spacing and backgrounds from all containers */
.stContainer {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
    padding: 0px !important;
}

div[data-testid="stContainer"] {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
    background-color: transparent !important;
    padding: 0px !important;
}

/* Target column containers specifically */
div[data-testid="column"] {
    background-color: transparent !important;
    padding: 0px !important;
    margin: 0px !important;
}

/* Remove backgrounds from all div elements that might be causing bars */
div[class*="css-"] {
    background-color: transparent !important;
}

/* Target specific container classes that might be causing the bars */
.css-1d391kg, .css-12oz5g7, .css-1kyxreq {
    background-color: transparent !important;
    padding: 0px !important;
    margin: 0px !important;
}

/* Remove any default streamlit container styling */
[data-testid="stVerticalBlock"] {
    background-color: transparent !important;
    padding: 0px !important;
    margin: 0px !important;
}

[data-testid="stHorizontalBlock"] {
    background-color: transparent !important;
    padding: 0px !important;
    margin: 0px !important;
}

/* Additional targeting for any remaining white/light containers */
div[style*="background-color"] {
    background-color: transparent !important;
}

/* Ensure main content area has no background */
.main {
    background-color: transparent !important;
}

/* Remove any remaining default padding/margins from containers */
section[data-testid="stSidebar"] + div {
    background-color: transparent !important;
}

/* Target any remaining container elements */
.stApp > div {
    background-color: transparent !important;
}
</style>
""", unsafe_allow_html=True)

class BookClubApp:
    def __init__(self):
        self.base_url = "https://openlibrary.org"
        self.search_url = "https://openlibrary.org/search.json"
        

        self.hf_api_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        self.hf_token = st.secrets.get("HUGGINGFACE_TOKEN", None) if hasattr(st, 'secrets') else None
        

        if not self.hf_token:
            self.hf_token = os.getenv("HUGGINGFACE_TOKEN")

    def call_huggingface_ai(self, prompt: str, max_length: int = 200) -> str:
        """Call Hugging Face API for AI text generation"""
        if not self.hf_token:
            return self._fallback_ai_response(prompt)
        
        try:
            headers = {"Authorization": f"Bearer {self.hf_token}"}

            api_url = "https://api-inference.huggingface.co/models/gpt2"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": max_length,
                    "temperature": 0.7,
                    "do_sample": True,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    # Clean up the response by removing the original prompt
                    if generated_text.startswith(prompt):
                        generated_text = generated_text[len(prompt):].strip()
                    return generated_text if generated_text else self._fallback_ai_response(prompt)
                else:
                    return self._fallback_ai_response(prompt)
            else:
                # If API fails, fall back to template-based response
                return self._fallback_ai_response(prompt)
                
        except Exception as e:
            st.warning(f"AI API temporarily unavailable. Using fallback response.")
            return self._fallback_ai_response(prompt)

    def _fallback_ai_response(self, prompt: str) -> str:
        """Fallback response when AI API is unavailable"""
        if "summary" in prompt.lower():
            return "This book offers readers a compelling narrative that explores deep themes and human experiences. The author weaves together engaging characters and thought-provoking scenarios that challenge readers to examine important life questions. Through masterful storytelling, this work provides both entertainment and insight into the human condition."
        else:
            return "This book presents fascinating themes that would make for excellent book club discussion. Consider exploring the character development, thematic elements, and how the story relates to contemporary issues."

    def search_books(self, genre: str = None, author: str = None, title: str = None, limit: int = 10) -> List[Dict]:
        """Search for books by genre, author, and/or title using Open Library API"""
        try:

            params = {
                'limit': limit,
                'has_fulltext': 'true',
                'fields': 'key,title,author_name,first_publish_year,subject,isbn,cover_i,ratings_average,ratings_count'
            }
            

            search_parts = []
            if title and title.strip():
                search_parts.append(f'title:"{title.strip()}"')
            if author and author.strip():
                search_parts.append(f'author:"{author.strip()}"')
            if genre and genre != "Any Genre":
                # Map user-friendly genres to search terms
                genre_mapping = {
                    "Fiction": "fiction",
                    "Mystery": "mystery",
                    "Romance": "romance",
                    "Science Fiction": "science fiction",
                    "Fantasy": "fantasy",
                    "Biography": "biography",
                    "History": "history",
                    "Self-Help": "self help",
                    "Business": "business",
                    "Philosophy": "philosophy",
                    "Psychology": "psychology",
                    "Poetry": "poetry",
                    "Horror": "horror",
                    "Thriller": "thriller",
                    "Adventure": "adventure"
                }
                search_term = genre_mapping.get(genre, genre.lower())
                search_parts.append(f'subject:"{search_term}"')
            

            if search_parts:
                params['q'] = ' AND '.join(search_parts)
            elif genre and genre != "Any Genre":
                params['subject'] = genre_mapping.get(genre, genre.lower())
            else:

                params['q'] = 'fiction'
            
            response = requests.get(self.search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            books = []
            for book in data.get('docs', []):
                if book.get('title') and book.get('author_name'):
                    books.append({
                        'title': book.get('title', 'Unknown Title'),
                        'authors': book.get('author_name', ['Unknown Author']),
                        'year': book.get('first_publish_year'),
                        'subjects': book.get('subject', [])[:5],  # Limit subjects
                        'isbn': book.get('isbn', [None])[0] if book.get('isbn') else None,
                        'cover_id': book.get('cover_i'),
                        'rating': book.get('ratings_average'),
                        'rating_count': book.get('ratings_count', 0)
                    })
            
            return books
            
        except Exception as e:
            st.error(f"Error fetching books: {str(e)}")
            return []

    def get_cover_url(self, cover_id: int, size: str = "M") -> str:
        """Get book cover URL from cover ID"""
        if cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"
        return None

    def generate_ai_summary(self, book_title: str, authors: List[str], subjects: List[str]) -> str:
        """Generate AI-powered book summary using Hugging Face API"""
        author_text = ", ".join(authors[:2])
        subjects_text = ", ".join(subjects[:3]) if subjects else "general literature"
        
        prompt = f"Write a thoughtful book summary: '{book_title}' by {author_text} is a book about {subjects_text}. This book"
        
        ai_response = self.call_huggingface_ai(prompt, max_length=250)
        

        if ai_response and len(ai_response) > 50:
            return f"'{book_title}' by {author_text} explores themes of {subjects_text}. {ai_response}"
        else:
            # Enhanced fallback with more variety
            templates = [
                f"'{book_title}' by {author_text} is a captivating work that delves into {subjects_text}. This book offers readers a unique perspective on human nature and society, weaving together compelling characters with thought-provoking scenarios. The author's masterful storytelling creates an immersive experience that challenges readers to examine their own beliefs and assumptions.",
                f"In '{book_title}', {author_text} delivers a powerful narrative centered around {subjects_text}. The book presents a rich tapestry of characters and situations that illuminate deeper truths about the human condition. Readers will find themselves drawn into a world that is both familiar and surprising, with insights that linger long after the final page.",
                f"'{book_title}' by {author_text} stands as a remarkable exploration of {subjects_text}. The work combines engaging storytelling with profound insights, offering readers both entertainment and enlightenment. Through skillful character development and plot construction, the author creates a memorable reading experience that resonates with diverse audiences."
            ]
            return random.choice(templates)

    def generate_discussion_questions(self, book_title: str, authors: List[str], subjects: List[str]) -> List[str]:
        """Generate AI-powered discussion questions using Hugging Face API"""
        author_text = authors[0] if authors else "the author"
        subject_text = subjects[0] if subjects else "life"
        

        ai_questions = []
        if self.hf_token:
            try:
                prompt = f"Generate discussion questions for the book '{book_title}' about {subject_text}. Question 1:"
                ai_response = self.call_huggingface_ai(prompt, max_length=150)
                if ai_response and "?" in ai_response:
                    # Extract questions from AI response
                    potential_questions = [q.strip() + "?" for q in ai_response.split("?") if q.strip()]
                    ai_questions.extend(potential_questions[:2])
            except:
                pass
        

        base_questions = [
            f"What do you think {author_text} was trying to convey about {subject_text} in '{book_title}'?",
            f"How do the characters in '{book_title}' reflect real-world challenges and situations?",
            f"What themes in '{book_title}' are most relevant to today's society?",
            f"How does the author's writing style contribute to the overall impact of '{book_title}'?",
            f"What personal connections did you make while reading '{book_title}'?",
            f"What questions would you like to ask {author_text} about '{book_title}'?",
            f"How might '{book_title}' influence readers' perspectives on important life decisions?",
            "What scenes or passages from the book do you think would spark the most debate in our book club?",
            "If you were to recommend this book to a friend, what would you tell them to expect?"
        ]
        

        if subjects:
            for subject in subjects[:2]:
                base_questions.append(f"How does '{book_title}' approach the topic of {subject} differently from other books you've read?")
        

        all_questions = ai_questions + base_questions
        return random.sample(all_questions, min(8, len(all_questions)))

def main():
    st.title("📚 Virtual Book Club")    

    st.markdown("""
    - **Locate** books matching your criteria
    - **Generate** thoughtful summaries and analysis
    - **Formulate** engaging discussion questions

    """)
    
    with st.sidebar:
        st.header("🤖 AI Configuration")
        hf_token = st.text_input(
            "Hugging Face Token (Optional)",
            type="password",
            help="Get a free token from huggingface.co/settings/tokens for enhanced AI responses"
        )
        if hf_token:
            st.session_state.hf_token = hf_token
            st.success("✅ AI Token configured!")
        

    app = BookClubApp()
    
    # Use token from sidebar if provided
    if hasattr(st.session_state, 'hf_token'):
        app.hf_token = st.session_state.hf_token
    
    # Main search section
    st.header("Find Your Book(s)")
    
    # Create 2x2 grid for input fields
    col1, col2 = st.columns(2)
    
    with col1:
        genres = [
            "Any Genre", "Fiction", "Mystery", "Romance", "Science Fiction",
            "Fantasy", "Biography", "History", "Self-Help", "Business",
            "Philosophy", "Psychology", "Poetry", "Horror", "Thriller", "Adventure"
        ]
        selected_genre = st.selectbox("Genre:", genres)
    
    with col2:
        book_limit = st.selectbox("Number of Results:", [5, 8, 10, 15], index=1)
    
    # Second row
    col3, col4 = st.columns(2)
    
    with col3:
        author_name = st.text_input("Author (optional):", placeholder="e.g., Jane Austen, Stephen King")
    
    with col4:
        book_title = st.text_input("Book Title (optional):", placeholder="e.g., Pride and Prejudice")
    

    search_button = st.button("🔍 Search for Books", type="primary", use_container_width=True)
    

    if author_name or book_title or selected_genre != "Any Genre":
        search_criteria = []
        if selected_genre != "Any Genre":
            search_criteria.append(f"**Genre:** {selected_genre}")
        if author_name:
            search_criteria.append(f"**Author:** {author_name}")
        if book_title:
            search_criteria.append(f"**Title:** {book_title}")
        
        st.markdown('<div class="search-info">', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle search
    if search_button:
        if not any([selected_genre != "Any Genre", author_name.strip(), book_title.strip()]):
            st.warning("⚠️ Please provide at least one search criterion (Genre, Author, or Title)")
        else:
            with st.spinner("🔍 Searching for books..."):
                books = app.search_books(
                    genre=selected_genre if selected_genre != "Any Genre" else None,
                    author=author_name.strip() if author_name.strip() else None,
                    title=book_title.strip() if book_title.strip() else None,
                    limit=book_limit
                )
                st.session_state.books = books
                st.session_state.search_performed = True
    
    # Display results
    if 'books' in st.session_state and st.session_state.get('search_performed'):
        if st.session_state.books:
            st.header(f"📚 Found {len(st.session_state.books)} Books")
            
            for i, book in enumerate(st.session_state.books):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    # Display book cover
                    cover_url = app.get_cover_url(book['cover_id'])
                    if cover_url:
                        try:
                            st.image(cover_url, width=120)
                        except:
                            st.info("📖 No cover available")
                    else:
                        st.info("📖 No cover available")
                
                with col2:
                    st.markdown(f"**{book['title']}**")
                    st.write(f"*by {', '.join(book['authors'][:2])}*")
                    
                    if book['year']:
                        st.write(f"📅 Published: {book['year']}")
                    
                    if book['rating']:
                        st.write(f"⭐ Rating: {book['rating']:.1f}/5 ({book['rating_count']} ratings)")
                    
                    # Display subjects as tags
                    if book['subjects']:
                        subjects_html = ""
                        for subject in book['subjects'][:3]:
                            subjects_html += f'<span class="genre-tag">{subject}</span>'
                        st.markdown(subjects_html, unsafe_allow_html=True)
                    
                    # Button to generate AI content for this book
                    if st.button(f"🤖 Click Here for Summary and Discussion Questions regarding '{book['title'][:30]}{'...' if len(book['title']) > 30 else ''}'", key=f"btn_{i}"):
                        with st.spinner("🧠 AI is reading and analyzing the book..."):
                            # Simulate AI processing time
                            time.sleep(1.5)
                            
                            # Generate AI summary
                            summary = app.generate_ai_summary(
                                book['title'],
                                book['authors'],
                                book['subjects']
                            )
                            
                            # Generate discussion questions
                            questions = app.generate_discussion_questions(
                                book['title'],
                                book['authors'],
                                book['subjects']
                            )
                            
                            # Display AI-generated content
                            st.markdown('<div class="book-card">', unsafe_allow_html=True)
                            st.subheader("🤖 AI-Generated Summary")
                            if app.hf_token:
                                st.info("✨ Enhanced by Hugging Face AI")
                            else:
                                st.info("💡 Basic AI response - add HF token in sidebar for enhanced summaries")
                            st.write(summary)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.markdown('<div class="discussion-section">', unsafe_allow_html=True)
                            st.subheader("💬 Discussion Questions")
                            for j, question in enumerate(questions, 1):
                                st.write(f"**{j}.** {question}")
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Reading recommendations
                            st.subheader("🎯 Book Club Recommendations")
                            rec_col1, rec_col2 = st.columns(2)
                            
                            with rec_col1:
                                st.write("**📋 For Discussion Leaders:**")
                                st.write("• Focus on questions 1-3 for initial discussion")
                                st.write("• Use questions 4-6 for deeper analysis")
                                st.write("• End with personal connection questions")
                                st.write("• Allow 15-20 minutes per major theme")
                            
                            with rec_col2:
                                st.write("**📖 For Members:**")
                                st.write("• Take notes on key themes while reading")
                                st.write("• Mark passages that resonate with you")
                                st.write("• Consider how the book relates to current events")
                                st.write("• Come prepared with your own questions")
                
                st.divider()
        
        else:
            st.warning("😔 No books found matching your criteria. Try:")
            st.write("• Broadening your search (use 'Any Genre')")
            st.write("• Checking spelling of author name or book title")
            st.write("• Using partial matches (e.g., just first name)")
    

if __name__ == "__main__":
    main()
