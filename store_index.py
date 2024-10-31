
from src.helper import load_pdf_file, text_split, download_hugging_face_embeddings
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os 



load_dotenv()

PINECONE_API_KEY = os.environ.get('972d5b82-e75a-43ba-b708-9f6622ccbbe')
os.environ["PINECONE_API_KEY"]="972d5b82-e75a-43ba-b708-9f6622ccbbe1"

extracted_data = load_pdf_file(Data='Data/')
text_chunks = text_split(extracted_data)
embeddings = download_hugging_face_embeddings()

pc = Pinecone(api_key="972d5b82-e75a-43ba-b708-9f6622ccbbe1")

index_name = "edubot"

pc.create_index(
    name=index_name,
    dimension=384,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

# embed each chunk and upsert the embeddings into your pinecone index
docsearch = PineconeVectorStore.from_documents(
    documents = text_chunks,
    index_name = index_name,
    embedding=embeddings,
)

