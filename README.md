# TIPQIC RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot system designed for the TIPQIC project, combining the power of large language models with domain-specific knowledge retrieval capabilities.

## 🚀 Features

- **Retrieval-Augmented Generation**: Combines information retrieval with generative AI for accurate, contextual responses
- **Domain-Specific Knowledge**: Tailored for TIPQIC project requirements and documentation
- **Interactive Chat Interface**: User-friendly conversational interface
- **Document Processing**: Ability to ingest and process various document formats
- **Semantic Search**: Advanced search capabilities using vector embeddings
- **Real-time Responses**: Fast and efficient query processing

## 🛠️ Technology Stack

- **Backend**: Python-based RAG implementation
- **Vector Database**: For storing and retrieving document embeddings
- **Language Model**: Integration with state-of-the-art LLMs
- **Document Processing**: Support for PDF, TXT, and other formats
- **Web Framework**: For API and web interface development

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/TIPQIC-RAG-chatbot.git
   cd TIPQIC-RAG-chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys and configuration
   ```

## 🚀 Quick Start

1. **Start the application**
   ```bash
   python app.py
   ```

2. **Access the chatbot**
   - Open your browser and navigate to `http://localhost:5000`
   - Or use the API endpoints directly

3. **Upload documents** (if applicable)
   - Use the document upload feature to add domain-specific knowledge
   - The system will process and index the documents automatically

## 📖 Usage

### Basic Chat
```python
# Example API usage
import requests

response = requests.post('http://localhost:5000/chat', json={
    'message': 'What is TIPQIC about?'
})
print(response.json()['response'])
```

### Document Upload
```python
# Upload documents for knowledge base
files = {'document': open('tipqic_docs.pdf', 'rb')}
response = requests.post('http://localhost:5000/upload', files=files)
```

## 🏗️ Project Structure

```
TIPQIC-RAG-chatbot/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # Project documentation
├── src/                  # Source code
│   ├── models/           # Data models
│   ├── services/         # Business logic
│   ├── utils/            # Utility functions
│   └── config/           # Configuration files
├── data/                 # Data storage
│   ├── documents/        # Document storage
│   └── embeddings/       # Vector embeddings
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS)
└── tests/                # Test files
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
HUGGINGFACE_API_KEY=your_huggingface_key

# Database Configuration
VECTOR_DB_URL=your_vector_database_url
DATABASE_NAME=tipqic_rag

# Application Settings
PORT=5000
DEBUG=True
MAX_TOKENS=2048
TEMPERATURE=0.7

# Document Processing
MAX_FILE_SIZE=10MB
SUPPORTED_FORMATS=pdf,txt,docx
```

## 🔧 API Endpoints

### Chat Endpoint
- **POST** `/chat`
  - Send a message to the chatbot
  - Request body: `{"message": "your question"}`
  - Response: `{"response": "chatbot answer", "sources": [...]}`

### Document Management
- **POST** `/upload` - Upload documents to knowledge base
- **GET** `/documents` - List uploaded documents
- **DELETE** `/documents/{id}` - Remove document from knowledge base

### Health Check
- **GET** `/health` - Check application status

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Run specific test file
python -m pytest tests/test_chatbot.py
```

## 📊 Performance Optimization

- **Caching**: Implement response caching for frequently asked questions
- **Batch Processing**: Process multiple documents simultaneously
- **Vector Optimization**: Use optimized vector search algorithms
- **Resource Management**: Monitor memory and CPU usage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions and support:

- Create an issue on GitHub
- Contact the development team
- Check the [documentation](docs/) for detailed guides

## 🔮 Roadmap

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Integration with external APIs
- [ ] Mobile application support
- [ ] Voice interaction capabilities
- [ ] Enhanced document processing
- [ ] Real-time collaboration features

## 📚 Additional Resources

- [RAG Implementation Guide](docs/rag-guide.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

---

**TIPQIC RAG Chatbot** - Empowering conversations with intelligent document retrieval and generation.