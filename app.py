from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_mail import Mail, Message
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.chains import create_retrieval_chain
# from langchain_core.chains import create_stuff_documents_chain
from dotenv import load_dotenv
from src.prompt import *
import os
import sqlite3
from datetime import datetime
import random
import requests
import time
from bs4 import BeautifulSoup
import pdfplumber

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")  # Secret key for session encryption

load_dotenv()

# Email configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='hingadbhavya96@gmail.com',
    MAIL_PASSWORD='gxvddbfyldxuwdak'
)
mail = Mail(app)

# Load API keys
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Embedding and model setup
embeddings = download_hugging_face_embeddings()
index_name = "edubot"
docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 5})

llm = ChatGroq(
    model="gemma2-9b-it",
    temperature=0.7,
    max_tokens=4092,
    max_retries=2
)

system_prompt = """
You are an assistant for answering career advice questions, providing supportive responses, and handling greetings and gratitude. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, say that you don't know. 
When a user greets you, respond with a friendly greeting. 
When a user expresses gratitude, respond with a warm and appreciative message. 
Keep your answers concise, using three sentences maximum.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Context: {context}\nQuestion: {input}")
])

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# Database initialization
def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otps (
            email TEXT,
            otp TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
    conn.commit()
    conn.close()

# Store chat history with user association
def store_chat_history(user_id, user_message, bot_response):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO chat_history (user_id, user_message, bot_response) VALUES (?, ?, ?)''',
                   (user_id, user_message, bot_response))
    conn.commit()
    conn.close()

# Routes
@app.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/otp-page")
def otp_page():
    return render_template("otp.html")

@app.route("/signup", methods=["POST"])
def signup():
    data = request.form
    email = data["email"]
    password = data["password"]
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already exists."}), 400
    finally:
        conn.close()
    return jsonify({"message": "Signup successful."})

@app.route("/login", methods=["POST"])
def login():
    data = request.form
    email = data["email"]
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    if user:
        otp = str(random.randint(100000, 999999))
        cursor.execute("INSERT INTO otps (email, otp) VALUES (?, ?)", (email, otp))
        conn.commit()
        msg = Message("Your OTP for EDUBOT", sender="your-email@gmail.com", recipients=[email])
        msg.body = f"Your OTP is: {otp}"
        mail.send(msg)
        return redirect(url_for('otp_page'))
    else:
        return jsonify({"message": "Email not registered."}), 400

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.form
    email = data["email"]
    otp = data["otp"]
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM otps WHERE email = ? AND otp = ?", (email, otp))
    result = cursor.fetchone()
    if result:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]  # Store user ID in session
        return redirect(url_for('chatbot'))
    else:
        return jsonify({"message": "Invalid OTP."}), 400

@app.route("/")
def index():
    return redirect(url_for("login_page"))

@app.route("/chat")
def chatbot():
    return render_template('chat.html')

@app.route("/get", methods=["POST"])
def chat():
    msg = request.form["msg"]
    user_id = session.get('user_id')  # Retrieve current user from session

    if len(msg.split()) < 5 and "career" in msg.lower():
        response = "Could you clarify what you're looking for? For example, are you asking about skills, job roles, or education?"
    else:
        response = rag_chain.invoke({"input": msg})["answer"]

    # Optional: Add web search logic here as before
    if user_id:
        store_chat_history(user_id, msg, response)
    return response

@app.route("/analyze-skills", methods=["POST"])
def analyze_skills():
    resume_file = request.files.get("resume")
    job_description = request.form.get("job_description", "")
    if not resume_file or not job_description:
        return jsonify({"error": "Resume or job description missing"}), 400
    resume_text = ""
    if resume_file.filename.endswith(".pdf"):
        with pdfplumber.open(resume_file) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""
    resume_words = set(resume_text.lower().split())
    jd_skills = set(job_description.lower().split(","))
    resume_skills = [skill.strip() for skill in jd_skills if skill.strip() in resume_words]
    missing_skills = [skill.strip() for skill in jd_skills if skill.strip() not in resume_words]
    course_suggestions = {}
    for skill in missing_skills:
        coursera_links = search_coursera(skill)
        course_suggestions[skill] = coursera_links
    return jsonify({
        "resume_skills": resume_skills,
        "missing_skills": missing_skills,
        "course_suggestions": course_suggestions
    })

@app.route("/history")
def history():
    user_id = session.get('user_id')  # Only show current user's history
    if not user_id:
        return jsonify([])
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, bot_response, timestamp FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {"user_message": row[0], "bot_response": row[1], "timestamp": row[2]}
        for row in rows
    ])

@app.route("/clear-history", methods=["POST"])
def clear_history():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return jsonify({"message": "Chat history cleared."})

# Web search functions
def duckduckgo_search(query):
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers)
    if response.status_code == 202:
        print("Rate limit hit! Retrying...")
        time.sleep(10)
        return duckduckgo_search(query)
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("a", class_="result__a")
    links = [result["href"] for result in results if "href" in result.attrs]
    return links

def web_search(query):
    job_keywords = ["job", "jobs", "career", "employment", "hiring", "recommendation"]
    job_sites = ["indeed.com", "linkedin.com/jobs", "glassdoor.com", "monster.com", "simplyhired.com"]
    if any(keyword in query.lower() for keyword in job_keywords):
        site_filters = " OR ".join([f"site:{site}" for site in job_sites])
        search_query = f"{query} {site_filters}"
    else:
        search_query = query
    search_results = duckduckgo_search(search_query)
    formatted_results = [f'<a href="{link}" target="_blank">{link}</a>' for link in search_results]
    return formatted_results

def search_coursera(skill):
    query = f"{skill.replace(' ', '+')}+course"
    search_url = f"https://www.coursera.org/search?query={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    course_links = []
    for link in soup.select("a[href^='/learn']"):
        course_url = "https://www.coursera.org" + link["href"]
        course_links.append(course_url)
        if len(course_links) >= 3:
            break
    return course_links

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)