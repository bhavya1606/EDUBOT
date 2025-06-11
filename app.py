from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_mail import Mail, Message
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import sqlite3
import random
import pdfplumber
import requests
from bs4 import BeautifulSoup

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback-secret-key-for-dev")
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

# Load GROQ API key
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Use only Groq LLM
llm = ChatGroq(
    model="gemma2-9b-it",
    temperature=0.7,
    max_tokens=4092,
    groq_api_key=GROQ_API_KEY
)

# Prompt template
system_prompt = """
You are an assistant for answering career advice questions.
If unsure, say you don't know.
When a user greets you, respond warmly.
When a user thanks you, respond appreciatively.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Question: {input}")
])

chain = prompt | llm

# Database setup
def init_db():
    os.makedirs('/app', exist_ok=True)
    conn = sqlite3.connect('/app/chat_history.db')
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

def store_chat_history(user_id, user_message, bot_response):
    conn = sqlite3.connect('/app/chat_history.db')
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
    conn = sqlite3.connect('/app/chat_history.db')
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
    conn = sqlite3.connect('/app/chat_history.db')
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
    conn = sqlite3.connect('/app/chat_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM otps WHERE email = ? AND otp = ?", (email, otp))
    result = cursor.fetchone()
    if result:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
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
        response = chain.invoke({"input": msg}).content

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
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])
    conn = sqlite3.connect('/app/chat_history.db')
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
    conn = sqlite3.connect('/app/chat_history.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return jsonify({"message": "Chat history cleared."})

# Web search functions
def duckduckgo_search(query):
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    links = [result["href"] for result in soup.find_all("a", class_="result__a", href=True)]
    return links[:5]

def search_coursera(skill):
    query = f"{skill.replace(' ', '+')}+course"
    search_url = f"https://www.coursera.org/search?query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
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