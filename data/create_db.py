import os
import shutil

from dotenv import load_dotenv
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFium2Loader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
# Use os.path.join for cross-platform path handling
DATA_PATH = "./data/sources"


def load_documents():
    print("Loading PDF documents from a folder...")

    pdf_files = []
    for root, _, files in os.walk(DATA_PATH):
        for file in files:
            if file.endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"No PDF files found in {DATA_PATH}")
        return []

    print(f"Found {len(pdf_files)} PDF files")

    documents = []
    for pdf_file in pdf_files:
        try:
            file_name = os.path.basename(pdf_file)
            print(f"Loading: {file_name}")

            loader = PyPDFium2Loader(pdf_file)
            file_docs = loader.load()
            documents.extend(file_docs)
            print(f"  - Loaded {len(file_docs)} pages from {file_name}")

        except Exception as e:
            print(f"  - Error loading {file_name}: {e}")

    print(f"Successfully loaded {len(documents)} pages from {len(pdf_files)} PDF files")
    return documents


def split_text(documents: list[Document]):
    print("Split documents into chunks.")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )

    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks


CHROMA_PATH = "./chroma"

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", task_type="retrieval_document"
)

# Initialize Chroma DB
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)


def save_to_chroma(chunks: list[Document]):
    print("Clear previous db, and save the new db.")
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # create db
    Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)

    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


def create_vector_db():
    print("Create vector DB from personal PDF files.")
    documents = load_documents()
    doc_chunks = split_text(documents)
    save_to_chroma(doc_chunks)

def add_chunks_to_chroma(chunks: list[dict]):
    """
    Add chunks to the Chroma database without clearing it.
    """
    print("Adding chunks to the Chroma DB...")

    # Convert the incoming chunks into Document objects
    documents = [Document(page_content=chunk["content"], metadata=chunk["metadata"]) for chunk in chunks]

    # Add the documents to the Chroma database
    db.add_documents(documents)

    # Persist the updated database
    db.persist()

    print(f"Added {len(chunks)} chunks to the Chroma DB.")
    return {"message": f"Successfully added {len(chunks)} chunks to the Chroma DB."}


if __name__ == "__main__":
    create_vector_db()
