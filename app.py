from flask import Flask, render_template, jsonify, request
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
# from langchain_openai import OpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os



app = Flask(__name__)
load_dotenv()

PINECONE_API_KEY = os.environ.get('972d5b82-e75a-43ba-b708-9f6622ccbbe')
GROQ_API_KEY = os.environ.get("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")


os.environ["PINECONE_API_KEY"]="972d5b82-e75a-43ba-b708-9f6622ccbbe1"
os.environ["GROQ_API_KEY"]="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"

embeddings = download_hugging_face_embeddings()

index_name = "edubot"

#load existing index
from langchain_pinecone import PineconeVectorStore
docsearch = PineconeVectorStore.from_existing_index(
    index_name = index_name,
    embedding=embeddings,
)

retriver = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})

# Instantiate the Groq model
llm = ChatGroq(
    model="mixtral-8x7b-32768",  # Specify your desired model here
    temperature=0.4,
    max_tokens=500,
    max_retries=2  # Optional parameter for retries
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human","{input}"),
    ]
)
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriver,question_answer_chain)


@app.route("/")
def index():
    return render_template('chat.html')

@app.route("/get",methods=["GET","POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    print(input)
    response = rag_chain.invoke({"input" : msg})
    print("Response : ",response["answer"])
    return str(response["answer"])

if __name__=='__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)