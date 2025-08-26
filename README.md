# TIPQIC RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot system designed for the TIPQIC project. This chatbot combines document retrieval with Google's Gemini AI to provide intelligent, context-aware responses based on your document collection.

## 🚀 Features

- **Document Processing**: Automatically extracts and processes PDF documents
- **Vector Database**: Uses Chroma DB for efficient document storage and retrieval
- **Smart Chunking**: Intelligently splits documents with configurable chunk sizes and overlaps
- **Semantic Search**: Powered by Google's embedding models for accurate document retrieval
- **AI Responses**: Generates natural, conversational responses using Google Gemini
- **Multiple Interfaces**: Command-line and interactive chat modes
- **Source Attribution**: Provides source citations with page numbers
- **Confidence Scoring**: Shows relevance scores for retrieved information

## 🛠️ Technology Stack

- **Backend**: Python 3.8+
- **Vector Database**: Chroma DB
- **Embeddings**: Google Generative AI Embeddings (text-embedding-004)
- **Language Model**: Google Gemini Pro
- **PDF Processing**: PyPDFLoader, PyMuPDF, or pdfplumber
- **Framework**: LangChain for RAG implementation

## 📋 Prerequisites

- Python 3.8 or higher
- Google AI API Key (for Gemini and embeddings)
- pip (Python package installer)
- Git

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TIPQIC-RAG-chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .rag_env
   
   # On Windows
   .rag_env\Scripts\activate
   
   # On macOS/Linux
   source .rag_env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```
   
   Get your Google AI API key from: https://makersuite.google.com/app/apikey

## 📁 Project Structure

```
TIPQIC-RAG-chatbot/
├── data/
│   ├── create_db.py          # Database creation script
│   ├── sources/              # Place your PDF documents here
│   └── pdfExtractorTest.ipynb # PDF extraction testing
├── query/
│   ├── query_db.py           # Database search functionality
│   └── chatbot_response.py   # Chat response generation
├── chroma/                   # Vector database storage
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🚀 Quick Start

### Step 1: Add Your Documents

Place your PDF documents in the `data/sources/` directory:

```bash
mkdir -p data/sources
# Copy your PDF files to data/sources/
```

### Step 2: Create the Vector Database

Process your documents and create the searchable database:

```bash
python data/create_db.py
```

This will:
- Extract text from all PDFs in sources
- Split the text into chunks
- Generate embeddings
- Store everything in the Chroma vector database

### Step 3: Set up backend and frontend
   #### Linux

   Run this command: `start_services.sh` to start services

   Run this command: `stop_services.sh` to stop services

   #### Window   

   From root folder, run this command to set up backend:
   `python api/main.py`

   From root folder, run this command to set up frontend:
   `streamlit run frontend/app.py`

### (OPTIONAL) To create database
1. Create a folder `sources` inside folder `data`
2. Put all documents you want to handle inside `sources`
3. Navigate to folder `data`
4. From folder `data`, run `python create_db.py`

## 💬 Usage Examples

### Command Line Query
#### a. Get response solely from retrieved documents
```bash
python query/query_db.py "How does machine learning work in this project?"
```

Output:
```
Question: How does machine learning work in this project?
============================================================
🔍 Generating response...

💬 Response:
Based on the documents, machine learning in the TIPQIC project...

📚 Based on 3 relevant sources
```

#### b. Get response from retrieved documents AND LLM background knowledge
```bash
python query/chatbot_response.py 'How does ML work in this project?'
```

Output:
```
Question: 'How is Machine learning used in this project'
============================================================
🔍 Found relevant information, generating response...

💬 Response:
The provided documents do not contain information about the use of machine learning (ML) in the AHCCCS Targeted Investments (TI 2.0) project. Therefore, I cannot answer your question using the provided context.

Based on my general knowledge, machine learning could potentially be used in a project like this for:

*   **Predictive modeling:** To forecast performance on incentivized measures based on various factors.
*   **Data analysis:** To identify patterns and insights in the data related to health equity and quality improvement.
*   **Personalized recommendations:** To suggest tailored interventions or best practices to participants based on their specific needs and performance.

However, without specific information about the TI 2.0 project, I cannot confirm whether ML is actually used or how it is implemented.

============================================================

Sources used:
1. TI2.0ProgramWelcomePacket.pdf (Page 10) - Relevance: 0.191
2. TI2.0ProgramWelcomePacket.pdf (Page 4) - Relevance: 0.187
3. TI2.0ProgramWelcomePacket.pdf (Page 10) - Relevance: 0.180
4. TI2.0ProgramWelcomePacket.pdf (Page 9) - Relevance: 0.179
5. TI2.0ProgramWelcomePacket.pdf (Page 9) - Relevance: 0.175
```

### Interactive Chat
```bash
python query/query_db.py --chat
```

```
🤖 TIPQIC RAG Chatbot
Ask me questions about your documents!
Type 'quit', 'exit', or 'bye' to stop
==================================================

👤 You: What are the main objectives of TIPQIC?

🤖 Bot: According to the documentation, the main objectives of TIPQIC include...

👤 You: Can you tell me more about the methodology?

🤖 Bot: Building on the previous context about objectives, the methodology...
```

## ⚙️ Configuration

### Chunk Size Settings

In create_db.py, you can adjust text chunking:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,        # Characters per chunk
    chunk_overlap=100,     # Overlap between chunks
    length_function=len,
    add_start_index=True,
)
```

**Recommendations:**
- **Small chunks (200-500)**: Better for precise Q&A
- **Large chunks (800-1500)**: Better for contextual understanding
- **Overlap**: 20-30% of chunk size for continuity

### PDF Processing Options

The system supports multiple PDF extraction methods. You can modify `load_documents()` in `create_db.py`:

1. **PyPDFLoader** (default): Good balance of speed and accuracy
2. **PyMuPDF**: Better formatting preservation
3. **pdfplumber**: Best for complex layouts

### Embedding Models

Currently uses Google's `text-embedding-004`. To switch to open-source alternatives, see the embedding options in the codebase.

## 🔍 Search Features

- **Semantic Search**: Finds conceptually related content, not just keyword matches
- **Relevance Scoring**: Shows confidence levels for retrieved information
- **Source Attribution**: Provides document names and page numbers
- **Multi-document**: Searches across your entire document collection

## 📊 Advanced Usage

### Batch Processing
```bash
# Process multiple document sets
python data/create_db.py --data-path "./documents/set1"
python data/create_db.py --data-path "./documents/set2"
```

### Custom Search Parameters
```python
# In your own scripts
from query.query_db import search_db

results = search_db(
    query="your question",
    db_path="./chroma",
    k=10  # Return top 10 results
)
```

## 🧪 Testing PDF Extraction

Use the provided notebook to test different PDF extraction methods:

```bash
jupyter notebook data/pdfExtractorTest.ipynb
```

This helps you choose the best extraction method for your specific documents.

## 🚨 Troubleshooting

### Common Issues

**1. "No PDF files found"**
- Ensure PDFs are in sources directory
- Check file permissions

**2. "Google API Error"**
- Verify your `GOOGLE_API_KEY` in .env file
- Check API quota and billing

**3. "Chroma database error"**
- Delete chroma directory and recreate: `python data/create_db.py`

**4. "Poor search results"**
- Try different chunk sizes
- Test different PDF extraction methods
- Ensure documents are text-based (not scanned images)

### Performance Tips

- **Large documents**: Increase chunk size to 800-1200 characters
- **Many documents**: Consider using batch processing
- **Slow queries**: Reduce the number of returned results (k parameter)

## 📝 API Reference

### Core Functions

**`create_db.py`**
- `load_documents()`: Extract text from PDFs
- `split_text()`: Chunk documents
- `save_to_chroma()`: Store in vector database

**`query_db.py`**
- `search_db(query, db_path, k)`: Search the database
- `generate_chat_response()`: Generate AI responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
1. Check the troubleshooting section above
2. Review existing GitHub issues
3. Create a new issue with detailed information

## 🔮 Roadmap

- [ ] Web interface with Streamlit/Flask
- [ ] Support for more document formats (Word, Excel, etc.)
- [ ] Multi-language support
- [ ] Advanced filtering and search options
- [ ] Document summarization features
- [ ] Integration with other LLM providers
- [ ] Conversation memory and context tracking

---

**TIPQIC RAG Chatbot** - Making your documents conversational with AI! 🤖📚