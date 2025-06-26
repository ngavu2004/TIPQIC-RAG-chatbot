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

# search the DB
def search_db(query: str, db_path: str = "chroma/") -> list[Document]:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_query")
    db = Chroma(persist_directory=db_path, embedding_function=embeddings)
    
    # Use the correct method for text similarity search with scores
    results = db.similarity_search_with_relevance_scores(query, k=5)

    return results

def format_content_for_display(content: str, max_length: int = 200) -> str:
    """Format content for display while preserving meaningful whitespace."""
    # Strip leading/trailing whitespace but preserve internal formatting
    content = content.strip()
    
    if len(content) <= max_length:
        return content
    
    # Find a good breaking point near max_length
    preview = content[:max_length]
    
    # Try to break at a sentence or word boundary
    last_period = preview.rfind('.')
    last_space = preview.rfind(' ')
    
    if last_period > max_length - 50:  # If period is reasonably close to end
        preview = content[:last_period + 1]
    elif last_space > max_length - 30:  # If space is reasonably close to end
        preview = content[:last_space]
    
    return preview + "..."

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python query/query_db.py 'your search query here'")
        print("Example: python query/query_db.py 'What is TIPQIC about?'")
        sys.exit(1)
    
    # Get the query from command line arguments
    query = " ".join(sys.argv[1:])  # Join all arguments after the script name
    
    print(f"Searching for: '{query}'")
    
    try:
        results = search_db(query)
        
        if results:
            print(f"\nFound {len(results)} results:")
            print("-" * 50)
            
            for i, (doc, score) in enumerate(results, 1):
                print(f"Result {i} (Score: {score:.4f}):")
                print(f"Source: {doc.metadata.get('source', 'Unknown')}")
                
                formatted_content = format_content_for_display(doc.page_content, 200)
                print("Content:")
                print(formatted_content)
                print("-" * 50)
        else:
            print("No results found.")
            
    except Exception as e:
        print(f"Error during search: {e}")