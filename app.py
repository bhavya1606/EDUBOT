from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_mail import Mail, Message
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
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
load_dotenv()

# Environment variables
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='hingadbhavya96@gmail.com',
    MAIL_PASSWORD='gxvddbfyldxuwdak'
)
mail = Mail(app)

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

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

def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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

def store_chat_history(user_message, bot_response):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO chat_history (user_message, bot_response) VALUES (?, ?)''', (user_message, bot_response))
    conn.commit()
    conn.close()

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
    if len(msg.split()) < 5 and "career" in msg.lower():
        return "Could you clarify what you're looking for? For example, are you asking about skills, job roles, or education?"
    response = rag_chain.invoke({"input": msg})
    bot_response = response["answer"]
    if "find" in msg.lower() or any(keyword in msg.lower() for keyword in ["job", "jobs", "recommendation"]):
        search_results = web_search(msg)
        if search_results:
            formatted_links = "\n\n ---> **Job Opportunities Found:**\n" if any(keyword in msg.lower() for keyword in ["job", "jobs", "recommendation"]) else "\n\n ---> **Useful Resources:**\n"
            formatted_links += "\n".join(f"{i+1}. {result}" for i, result in enumerate(search_results))
            bot_response += formatted_links
        else:
            bot_response += "\n\n❌ No relevant opportunities found."
    store_chat_history(msg, bot_response)
    return bot_response

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


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))  # Render injects PORT
    app.run(host='0.0.0.0', port=port)
