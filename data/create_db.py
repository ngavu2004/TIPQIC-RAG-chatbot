from dotenv import load_dotenv
import os
import shutil
from langchain_chroma import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader

load_dotenv()
# Use os.path.join for cross-platform path handling
DATA_PATH = "./data/sources"

def load_documents():
    print("Loading PDF documents from a folder...")
    import pypdf
    from langchain.schema import Document
    
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
            
            # Use pypdf directly for faster loading
            with open(pdf_file, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                for i, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():  # Only include non-empty pages
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": pdf_file,
                                "page": i + 1,
                                "total_pages": len(pdf_reader.pages)
                            }
                        )
                        documents.append(doc)
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

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_document")


def save_to_chroma(chunks: list[Document]):
    print("Clear previous db, and save the new db.")
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # create db
    db = Chroma.from_documents(
        chunks, embeddings, persist_directory=CHROMA_PATH
    )
    
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")

def create_vector_db():
    print("Create vector DB from personal PDF files.")
    documents = load_documents()
    doc_chunks = split_text(documents)
    save_to_chroma(doc_chunks)

if __name__ == "__main__":    
    create_vector_db()