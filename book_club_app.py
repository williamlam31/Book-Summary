import streamlit as st
import requests
import json
import time
import random
from typing import Dict, List, Optional

# Configure Streamlit page
st.set_page_config(
    page_title="Virtual Book Club",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for better styling
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
</style>
""", unsafe_allow_html=True)

class BookClubApp:
    def __init__(self):
        self.base_url = "https://openlibrary.org"
        self.search_url = "https://openlibrary.org/search.json"
        
    def search_books(self, genre: str, limit: int = 10) -> List[Dict]:
        """Search for books by genre using Open Library API"""
        try:
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
                "Poetry": "poetry"
            }
            
            search_term = genre_mapping.get(genre, genre.lower())
            
            params = {
                'subject': search_term,
                'limit': limit,
                'has_fulltext': 'true',
                'fields': 'key,title,author_name,first_publish_year,subject,isbn,cover_i,ratings_average,ratings_count'
            }
            
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
        """Generate AI-powered book summary (simulated)"""
        # This is a simulated AI response - in a real implementation, 
        # you would integrate with an actual AI service like OpenAI, Anthropic, or local models
        
        author_text = ", ".join(authors[:2])  # Limit to first 2 authors
        subjects_text = ", ".join(subjects[:3]) if subjects else "general literature"
        
        # Template-based summary generation (simulating AI)
        templates = [
            f"'{book_title}' by {author_text} is a captivating work that explores themes of {subjects_text}. This book offers readers a unique perspective on human nature and society, weaving together compelling characters with thought-provoking scenarios. The author's masterful storytelling creates an immersive experience that challenges readers to examine their own beliefs and assumptions.",
            
            f"In '{book_title}', {author_text} delivers a powerful narrative centered around {subjects_text}. The book presents a rich tapestry of characters and situations that illuminate deeper truths about the human condition. Readers will find themselves drawn into a world that is both familiar and surprising, with insights that linger long after the final page.",
            
            f"'{book_title}' by {author_text} stands as a remarkable exploration of {subjects_text}. The work combines engaging storytelling with profound insights, offering readers both entertainment and enlightenment. Through skillful character development and plot construction, the author creates a memorable reading experience that resonates with diverse audiences."
        ]
        
        return random.choice(templates)
    
    def generate_discussion_questions(self, book_title: str, authors: List[str], subjects: List[str]) -> List[str]:
        """Generate AI-powered discussion questions (simulated)"""
        
        author_text = authors[0] if authors else "the author"
        subject_text = subjects[0] if subjects else "life"
        
        base_questions = [
            f"What do you think {author_text} was trying to convey about {subject_text} in '{book_title}'?",
            f"How do the characters in '{book_title}' reflect real-world challenges and situations?",
            f"What themes in '{book_title}' are most relevant to today's society?",
            f"How does the author's writing style contribute to the overall impact of '{book_title}'?",
            f"What personal connections did you make while reading '{book_title}'?"
        ]
        
        # Add subject-specific questions
        if subjects:
            for subject in subjects[:2]:
                base_questions.append(f"How does '{book_title}' approach the topic of {subject} differently from other books you've read?")
        
        base_questions.extend([
            f"What questions would you like to ask {author_text} about '{book_title}'?",
            f"How might '{book_title}' influence readers' perspectives on important life decisions?",
            "What scenes or passages from the book do you think would spark the most debate in our book club?",
            "If you were to recommend this book to a friend, what would you tell them to expect?"
        ])
        
        return random.sample(base_questions, 8)  # Return 8 random questions

def main():
    st.title("📚 Virtual Book Club")
    st.markdown("*Discover books, get AI-generated summaries, and spark meaningful discussions!*")
    
    app = BookClubApp()
    
    # Sidebar for genre selection
    st.sidebar.header("📖 Book Discovery")
    
    genres = [
        "Fiction", "Mystery", "Romance", "Science Fiction", "Fantasy",
        "Biography", "History", "Self-Help", "Business", "Philosophy",
        "Psychology", "Poetry"
    ]
    
    selected_genre = st.sidebar.selectbox("Choose a genre:", genres)
    book_limit = st.sidebar.slider("Number of books to fetch:", 3, 15, 8)
    
    if st.sidebar.button("🔍 Discover Books", type="primary"):
        with st.spinner("Searching for amazing books..."):
            books = app.search_books(selected_genre, book_limit)
            st.session_state.books = books
            st.session_state.selected_genre = selected_genre
    
    # Display books if they exist in session state
    if 'books' in st.session_state and st.session_state.books:
        st.header(f"📚 {st.session_state.selected_genre} Books")
        
        for i, book in enumerate(st.session_state.books):
            with st.container():
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
                if st.button(f"🤖 Generate Book Club Content", key=f"btn_{i}"):
                    with st.spinner("AI is reading and analyzing the book..."):
                        # Simulate AI processing time
                        time.sleep(1)
                        
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
                        st.subheader("📝 AI-Generated Summary")
                        st.write(summary)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="discussion-section">', unsafe_allow_html=True)
                        st.subheader("💬 Discussion Questions")
                        for j, question in enumerate(questions, 1):
                            st.write(f"**{j}.** {question}")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Reading recommendations
                        st.subheader("🎯 Book Club Recommendations")
                        st.write("**For Discussion Leaders:**")
                        st.write("- Focus on questions 1-3 for initial discussion")
                        st.write("- Use questions 4-6 for deeper analysis")
                        st.write("- End with personal connection questions")
                        
                        st.write("**For Members:**")
                        st.write("- Consider taking notes on key themes while reading")
                        st.write("- Mark passages that resonate with you")
                        st.write("- Think about how the book relates to current events")
                
                st.divider()
    
    else:
        # Welcome message
        st.markdown("""
        ## Welcome to Your Virtual Book Club! 🌟
        
        Get started by selecting a genre from the sidebar and clicking "Discover Books". 
        Our AI will help you:
        
        - 📚 **Discover** great books in your favorite genres
        - 📝 **Generate** thoughtful summaries and analysis  
        - 💭 **Create** engaging discussion questions
        - 🎯 **Provide** book club facilitation tips
        
        Perfect for book clubs, literature classes, or solo readers who want deeper insights!
        """)
        
        # Show some sample genres as buttons for quick access
        st.subheader("🚀 Quick Start - Try These Popular Genres:")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Mystery"):
                st.session_state.quick_genre = "Mystery"
        with col2:
            if st.button("🚀 Sci-Fi"):
                st.session_state.quick_genre = "Science Fiction"
        with col3:
            if st.button("💝 Romance"):
                st.session_state.quick_genre = "Romance"
        with col4:
            if st.button("📖 Fiction"):
                st.session_state.quick_genre = "Fiction"
        
        # Handle quick genre selection
        if 'quick_genre' in st.session_state:
            with st.spinner(f"Searching for {st.session_state.quick_genre} books..."):
                books = app.search_books(st.session_state.quick_genre, 6)
                st.session_state.books = books
                st.session_state.selected_genre = st.session_state.quick_genre
                del st.session_state.quick_genre
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        📚 Virtual Book Club | Powered by Open Library API & AI ✨<br>
        <small>Data sourced from <a href='https://openlibrary.org'>Open Library</a></small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

