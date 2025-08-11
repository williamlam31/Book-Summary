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
    .search-section {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 15px;
        margin: 5px 0 10px 0;
        border: 2px solid #e9ecef;
    }
    .search-info {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #bee5eb;
    }
    /* Remove default Streamlit spacing */
    .stMarkdown {
        margin-bottom: 0px;
    }
    div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0px;
    }
    .element-container {
        margin-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)

class BookClubApp:
    def __init__(self):
        self.base_url = "https://openlibrary.org"
        self.search_url = "https://openlibrary.org/search.json"
        
    def search_books(self, genre: str = None, author: str = None, title: str = None, limit: int = 10) -> List[Dict]:
        """Search for books by genre, author, and/or title using Open Library API"""
        try:
            # Build search parameters
            params = {
                'limit': limit,
                'has_fulltext': 'true',
                'fields': 'key,title,author_name,first_publish_year,subject,isbn,cover_i,ratings_average,ratings_count'
            }
            
            # Build search query based on inputs
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
            
            # If we have search parts, use 'q' parameter, otherwise use subject
            if search_parts:
                params['q'] = ' AND '.join(search_parts)
            elif genre and genre != "Any Genre":
                params['subject'] = genre_mapping.get(genre, genre.lower())
            else:
                # Default search if no criteria provided
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
        """Generate AI-powered book summary (simulated)"""
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
    
    # Main search section without extra div wrapper
    st.header("🔍 Find Your Perfect Book")
    
    # Create 2x2 grid for input fields
    col1, col2 = st.columns(2)
    
    with col1:
        genres = [
            "Any Genre", "Fiction", "Mystery", "Romance", "Science Fiction", 
            "Fantasy", "Biography", "History", "Self-Help", "Business", 
            "Philosophy", "Psychology", "Poetry", "Horror", "Thriller", "Adventure"
        ]
        selected_genre = st.selectbox("📖 Select Genre:", genres)
    
    with col2:
        book_limit = st.selectbox("📊 Number of Results:", [5, 8, 10, 15], index=1)
    
    # Second row
    col3, col4 = st.columns(2)
    
    with col3:
        author_name = st.text_input("✍️ Author Name (optional):", placeholder="e.g., Jane Austen, Stephen King")
    
    with col4:
        book_title = st.text_input("📚 Book Title (optional):", placeholder="e.g., Pride and Prejudice")
    
    # Search button below the 2x2 grid
    search_button = st.button("🔍 Search for Books", type="primary", use_container_width=True)
    
    # Display search info
    if author_name or book_title or selected_genre != "Any Genre":
        search_criteria = []
        if selected_genre != "Any Genre":
            search_criteria.append(f"**Genre:** {selected_genre}")
        if author_name:
            search_criteria.append(f"**Author:** {author_name}")
        if book_title:
            search_criteria.append(f"**Title:** {book_title}")
        
        st.markdown('<div class="search-info">', unsafe_allow_html=True)
        st.markdown(f"**🎯 Search Criteria:** {' | '.join(search_criteria)}")
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
                    if st.button(f"🤖 Generate Book Club Content for '{book['title'][:30]}{'...' if len(book['title']) > 30 else ''}'", key=f"btn_{i}"):
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
    
    # Welcome section (shown when no search has been performed)
    elif not st.session_state.get('search_performed'):
        st.markdown("""
        ## Welcome to Your Virtual Book Club! 🌟
        
        **How to get started:**
        1. 📖 **Select a genre** from the dropdown above (or leave as "Any Genre")
        2. ✍️ **Enter an author name** if you have someone specific in mind
        3. 📚 **Add a book title** if you're looking for something particular
        4. 🔍 **Click "Search for Books"** to discover amazing reads!
        
        Our AI will help you:
        - 📚 **Discover** books matching your criteria
        - 📝 **Generate** thoughtful summaries and analysis  
        - 💭 **Create** engaging discussion questions
        - 🎯 **Provide** book club facilitation tips
        
        Perfect for book clubs, literature classes, or solo readers who want deeper insights!
        
        ### 🚀 Quick Examples to Try:
        - **Genre:** Fantasy + **Author:** Brandon Sanderson
        - **Genre:** Mystery + **Title:** Murder
        - **Author:** Agatha Christie
        - **Genre:** Science Fiction (browse popular sci-fi books)
        """)
    
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
