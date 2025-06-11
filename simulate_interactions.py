from datetime import datetime, timedelta
import random
import sqlite3
from app import store_chat_history

# Sample realistic user messages
user_messages = [
    "What are the best careers for someone interested in tech?",
    "How do I become a data scientist?",
    "What skills are needed for software development?",
    "Can you suggest some good online courses for Python?",
    "I want to switch careers but don't know where to start.",
    "Tell me more about UX design as a career option.",
    "How can I improve my resume?",
    "What is the future of AI jobs?",
    "What are some entry-level IT jobs?",
    "What should I do if I'm not getting interviews?",
    "Where can I find remote work opportunities?",
    "I’m confused between marketing and finance careers.",
    "Can you recommend some Coursera courses?",
    "What does a product manager do?",
    "I got rejected from 10 jobs. What should I do?",
]

# Bot response templates
helpful_responses = [
    "Here are some top tech careers: Software Developer, Data Scientist, Cybersecurity Analyst, Cloud Architect...",
    "To become a data scientist, focus on learning Python, Statistics, Machine Learning, and build projects...",
    "Key skills for software development include coding (like Python or Java), problem-solving, debugging, and teamwork...",
    "You can take the 'Python for Everybody' course on Coursera or Google's Python Crash Course on Coursera...",
    "Start by identifying what interests you most—then upskill accordingly. You might explore fields like tech, healthcare, or business analytics.",
    "UX Design focuses on improving user satisfaction by enhancing usability and accessibility of products...",
    "Make sure your resume highlights relevant experience, uses action verbs, and includes keywords from job descriptions...",
    "AI-related roles like Machine Learning Engineer, NLP Engineer, and AI Researcher are expected to grow significantly...",
    "Entry-level IT jobs include Help Desk Technician, IT Support Specialist, Network Administrator, and Junior Developer roles.",
    "Focus on tailoring your resume, practicing mock interviews, and reaching out to mentors or professionals in your field.",
    "Try visiting platforms like We Work Remotely, RemoteOK, or LinkedIn with filters set to remote jobs.",
    "Marketing is more creative and customer-focused, while Finance involves numbers, risk analysis, and strategic planning.",
    "Coursera offers excellent courses like 'Data Science Specialization' by Johns Hopkins University and 'Machine Learning' by Andrew Ng.",
    "A Product Manager defines the product vision, works with engineering and design teams, and ensures the product meets user needs.",
    "Review feedback if available, improve your resume and interview skills, and consider taking on freelance or internship work to gain experience."
]

unhelpful_responses = [
    "I'm sorry, I don't have enough information to answer that.",
    "I'm not sure how to respond to that question.",
    "That topic is outside my current knowledge base.",
    "I can’t provide an accurate answer right now.",
    "Let me know if there’s something else I can assist you with!"
]

web_search_links = """
 ---> **Useful Resources:**
1. [Introduction to Data Science (Coursera)](https://www.coursera.org/course/datasci) 
2. [Top Python Courses on Udemy](https://udemy.com/topic/python/) 
3. [Remote IT Jobs at RemoteOK](https://remoteok.io/) 
"""

# Function to simulate storing chat history
def simulate_chats(num_interactions=20):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")  # Clear old data
    conn.commit()

    now = datetime.now()

    for i in range(num_interactions):
        user_msg = random.choice(user_messages)
        use_web_search = random.choice([True, False])
        is_helpful = random.choice([True, False])

        bot_response = random.choice(helpful_responses) if is_helpful else random.choice(unhelpful_responses)
        if use_web_search and is_helpful:
            bot_response += web_search_links

        # Add timestamp going back 7 days
        fake_time = now - timedelta(minutes=random.randint(1, 60*24*7))
        formatted_time = fake_time.strftime('%Y-%m-%d %H:%M:%S')

        # Insert into database
        cursor.execute('''
            INSERT INTO chat_history (user_message, bot_response, timestamp)
            VALUES (?, ?, ?)
        ''', (user_msg, bot_response, formatted_time))

    conn.commit()
    conn.close()
    print(f"{num_interactions} simulated chat entries added to chat_history.db")

if __name__ == "__main__":
    simulate_chats(num_interactions=30)  # Change number of interactions here