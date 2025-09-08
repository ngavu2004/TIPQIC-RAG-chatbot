import os
import shutil
import traceback
import tempfile
from typing import List, Optional

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

# OCR imports
try:
    from pdf2image import convert_from_path
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR dependencies not available. Install pdf2image and pytesseract for OCR support.")

load_dotenv()
# Use os.path.join for cross-platform path handling
DATA_PATH = "./data/sources"


def load_pdf_with_ocr(pdf_file: str) -> List[Document]:
    """
    Load PDF using OCR for image-based PDFs.
    Returns list of documents or empty list if OCR fails.
    """
    if not OCR_AVAILABLE:
        print("  - OCR not available, skipping OCR loader")
        return []
    
    file_name = os.path.basename(pdf_file)
    documents = []
    
    try:
        print(f"  - Converting PDF to images for OCR processing...")
        
        # Convert PDF to images
        images = convert_from_path(pdf_file, dpi=300)
        print(f"  - Converted to {len(images)} images")
        
        for page_num, image in enumerate(images):
            try:
                # Perform OCR on each page
                text = pytesseract.image_to_string(image, lang='eng')
                
                if text and text.strip():
                    # Create document with OCR text
                    doc = Document(
                        page_content=text.strip(),
                        metadata={
                            'source': pdf_file,
                            'page': page_num + 1,
                            'total_pages': len(images),
                            'method': 'OCR',
                            'file_name': file_name
                        }
                    )
                    documents.append(doc)
                    print(f"    - OCR extracted text from page {page_num + 1}")
                else:
                    print(f"    - Warning: No text extracted from page {page_num + 1}")
                    
            except Exception as e:
                print(f"    - Error processing page {page_num + 1} with OCR: {e}")
                continue
        
        if documents:
            print(f"  - OCR Success: {len(documents)} pages with content")
            return documents
        else:
            print(f"  - OCR failed: No content extracted")
            return []
            
    except Exception as e:
        print(f"  - OCR failed: {e}")
        return []


def load_pdf_with_fallback(pdf_file: str) -> List[Document]:
    """
    Try multiple PDF loaders with fallback system for better compatibility.
    Now includes OCR as the last fallback option for image-based PDFs.
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
    
    # If all standard loaders failed, try OCR as last resort
    print(f"  - All standard loaders failed, trying OCR for {file_name}")
    ocr_docs = load_pdf_with_ocr(pdf_file)
    if ocr_docs:
        return ocr_docs
    
    print(f"  - All loaders (including OCR) failed for {file_name}")
    return []


def load_documents():
    print("Loading PDF documents from a folder...")
    print(f"Looking in: {os.path.abspath(DATA_PATH)}")
    
    if OCR_AVAILABLE:
        print("OCR support: Available")
    else:
        print("OCR support: Not available (install pdf2image and pytesseract)")

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
    ocr_successful_files = 0
    
    for pdf_file in pdf_files:
        file_name = os.path.basename(pdf_file)
        print(f"\nLoading: {file_name}")
        
        file_docs = load_pdf_with_fallback(pdf_file)
        
        if file_docs:
            documents.extend(file_docs)
            successful_files += 1
            
            # Check if OCR was used
            if any(doc.metadata.get('method') == 'OCR' for doc in file_docs):
                ocr_successful_files += 1
                print(f"  - Successfully loaded {len(file_docs)} pages from {file_name} (using OCR)")
            else:
                print(f"  - Successfully loaded {len(file_docs)} pages from {file_name}")
            
            # Debug: Show sample content from first document
            if file_docs[0].page_content:
                sample_content = file_docs[0].page_content[:100].replace('\n', ' ')
                print(f"  - Sample content: {sample_content}...")
        else:
            print(f"  - Failed to load any content from {file_name}")

    print(f"\nSUMMARY: Successfully loaded {len(documents)} pages from {successful_files}/{len(pdf_files)} PDF files")
    if ocr_successful_files > 0:
        print(f"OCR was used for {ocr_successful_files} files")
    
    # Additional debugging for empty documents
    if documents:
        non_empty_docs = [doc for doc in documents if doc.page_content.strip()]
        print(f"Documents with content: {len(non_empty_docs)}/{len(documents)}")
        
        if len(non_empty_docs) < len(documents):
            empty_count = len(documents) - len(non_empty_docs)
            print(f"Warning: {empty_count} documents have empty content")
    
    return documents


def split_text(documents: List[Document]):
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


def save_to_chroma(chunks: List[Document]):
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


def add_chunks_to_chroma(chunks: List[dict]):
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
        print("5. For OCR support, install: pip install pdf2image pytesseract")
        print("6. On Windows, you may need to install poppler: https://github.com/oschwartz10612/poppler-windows")