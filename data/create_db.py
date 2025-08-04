import os
import shutil
import traceback

from dotenv import load_dotenv
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Import multiple PDF loaders for fallback
from langchain_community.document_loaders import (
    PyPDFium2Loader,
    PyPDFLoader,
    PDFMinerLoader,
    UnstructuredPDFLoader
)

load_dotenv()
# Use os.path.join for cross-platform path handling
DATA_PATH = "./data/sources"


def load_pdf_with_fallback(pdf_file: str) -> list[Document]:
    """
    Try multiple PDF loaders with fallback system for better compatibility.
    Returns list of documents or empty list if all loaders fail.
    """
    file_name = os.path.basename(pdf_file)
    
    # Define loaders in order of preference - PyPDFLoader first for Linux
    loaders = [
        ("PyPDFLoader", lambda: PyPDFLoader(pdf_file)),
        ("PyPDFium2Loader", lambda: PyPDFium2Loader(pdf_file)),
        ("PDFMinerLoader", lambda: PDFMinerLoader(pdf_file)),
        ("UnstructuredPDFLoader", lambda: UnstructuredPDFLoader(pdf_file))
    ]
    
    for loader_name, loader_func in loaders:
        try:
            print(f"  - Trying {loader_name} for {file_name}")
            loader = loader_func()
            file_docs = loader.load()
            
            # Validate that documents have content
            valid_docs = []
            for doc in file_docs:
                if doc.page_content and doc.page_content.strip():
                    valid_docs.append(doc)
                else:
                    print(f"    - Warning: Empty page content found")
            
            if valid_docs:
                print(f"  - Success with {loader_name}: {len(valid_docs)} pages with content")
                return valid_docs
            else:
                print(f"  - {loader_name} loaded {len(file_docs)} pages but all were empty")
                
        except ImportError as e:
            print(f"  - {loader_name} not available: {e}")
            continue
        except Exception as e:
            print(f"  - {loader_name} failed: {e}")
            continue
    
    print(f"  - All loaders failed for {file_name}")
    return []


def load_documents():
    print("Loading PDF documents from a folder...")
    print(f"Looking in: {os.path.abspath(DATA_PATH)}")

    if not os.path.exists(DATA_PATH):
        print(f"ERROR: Directory {DATA_PATH} does not exist!")
        return []

    pdf_files = []
    for root, _, files in os.walk(DATA_PATH):
        for file in files:
            if file.endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"No PDF files found in {DATA_PATH}")
        print("Available files:")
        try:
            for root, _, files in os.walk(DATA_PATH):
                for file in files:
                    print(f"  - {file}")
        except:
            print("  - Unable to list files")
        return []

    print(f"Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file}")

    documents = []
    successful_files = 0
    
    for pdf_file in pdf_files:
        file_name = os.path.basename(pdf_file)
        print(f"\nLoading: {file_name}")
        
        file_docs = load_pdf_with_fallback(pdf_file)
        
        if file_docs:
            documents.extend(file_docs)
            successful_files += 1
            print(f"  - Successfully loaded {len(file_docs)} pages from {file_name}")
            
            # Debug: Show sample content from first document
            if file_docs[0].page_content:
                sample_content = file_docs[0].page_content[:100].replace('\n', ' ')
                print(f"  - Sample content: {sample_content}...")
        else:
            print(f"  - Failed to load any content from {file_name}")

    print(f"\nSUMMARY: Successfully loaded {len(documents)} pages from {successful_files}/{len(pdf_files)} PDF files")
    
    # Additional debugging for empty documents
    if documents:
        non_empty_docs = [doc for doc in documents if doc.page_content.strip()]
        print(f"Documents with content: {len(non_empty_docs)}/{len(documents)}")
        
        if len(non_empty_docs) < len(documents):
            empty_count = len(documents) - len(non_empty_docs)
            print(f"Warning: {empty_count} documents have empty content")
    
    return documents


def split_text(documents: list[Document]):
    print("\nSplit documents into chunks.")
    
    # Filter out empty documents before splitting
    valid_documents = []
    for doc in documents:
        if doc.page_content and doc.page_content.strip():
            valid_documents.append(doc)
        else:
            print(f"Skipping empty document: {doc.metadata}")
    
    print(f"Processing {len(valid_documents)}/{len(documents)} non-empty documents")
    
    if not valid_documents:
        print("ERROR: No valid documents to split!")
        return []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )

    try:
        chunks = text_splitter.split_documents(valid_documents)
        print(f"Split {len(valid_documents)} documents into {len(chunks)} chunks.")
        
        # Debug: Show sample chunk
        if chunks:
            sample_chunk = chunks[0].page_content[:100].replace('\n', ' ')
            print(f"Sample chunk: {sample_chunk}...")
        
        return chunks
    except Exception as e:
        print(f"ERROR splitting documents: {e}")
        traceback.print_exc()
        return []


CHROMA_PATH = "./chroma"

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", task_type="retrieval_document"
)


def save_to_chroma(chunks: list[Document]):
    print("\nSaving to ChromaDB...")
    print(f"Database path: {os.path.abspath(CHROMA_PATH)}")
    
    if not chunks:
        print("ERROR: No chunks to save to database!")
        return False
    
    try:
        # Remove existing database
        if os.path.exists(CHROMA_PATH):
            print(f"Removing existing database at {CHROMA_PATH}")
            shutil.rmtree(CHROMA_PATH)

        # Create new database
        print(f"Creating database with {len(chunks)} chunks...")
        db = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        
        print(f"SUCCESS: Saved {len(chunks)} chunks to {CHROMA_PATH}")
        
        # Verify database was created
        if os.path.exists(CHROMA_PATH):
            files = os.listdir(CHROMA_PATH)
            print(f"Database files created: {files}")
            return True
        else:
            print("ERROR: Database directory was not created!")
            return False
            
    except Exception as e:
        print(f"ERROR creating database: {e}")
        traceback.print_exc()
        return False


def create_vector_db():
    print("Create vector DB from personal PDF files.")
    print("=" * 60)
    
    # Check environment
    print(f"Current working directory: {os.getcwd()}")
    print(f"GOOGLE_API_KEY set: {'GOOGLE_API_KEY' in os.environ}")
    
    documents = load_documents()
    
    if not documents:
        print("FAILED: No documents loaded. Cannot create vector database.")
        return False
    
    print("=" * 60)
    doc_chunks = split_text(documents)
    
    if not doc_chunks:
        print("FAILED: No chunks created. Cannot create vector database.")
        return False
    
    print("=" * 60)
    success = save_to_chroma(doc_chunks)
    
    if success:
        print("SUCCESS: Vector database creation completed!")
        return True
    else:
        print("FAILED: Vector database creation failed!")
        return False


# Don't initialize DB at module level to avoid permission issues
def get_chroma_db():
    """Get ChromaDB instance only when needed"""
    try:
        if not os.path.exists(CHROMA_PATH):
            print(f"Database not found at {CHROMA_PATH}")
            return None
        return Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    except Exception as e:
        print(f"Error loading database: {e}")
        return None


def add_chunks_to_chroma(chunks: list[dict]):
    """
    Add chunks to the Chroma database without clearing it.
    """
    print("Adding chunks to the Chroma DB...")
    
    db = get_chroma_db()
    if not db:
        return {"error": "Database not found or not accessible"}

    # Convert the incoming chunks into Document objects
    documents = [Document(page_content=chunk["content"], metadata=chunk["metadata"]) for chunk in chunks]

    try:
        # Add the documents to the Chroma database
        db.add_documents(documents)
        
        print(f"Added {len(chunks)} chunks to the Chroma DB.")
        return {"message": f"Successfully added {len(chunks)} chunks to the Chroma DB."}
    except Exception as e:
        print(f"Error adding chunks: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    success = create_vector_db()
    if not success:
        print("\nTroubleshooting steps:")
        print("1. Check if PDF files exist in data/sources/")
        print("2. Verify GOOGLE_API_KEY in .env file")
        print("3. Check if all dependencies are installed")
        print("4. Try running with: python -c 'import chromadb; print(chromadb.__version__)'")