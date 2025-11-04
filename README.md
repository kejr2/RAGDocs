# RAGDocs - AI Documentation Assistant

A full-stack RAG (Retrieval Augmented Generation) application that allows users to upload documentation (PDFs, Markdown, TXT, HTML) and query them using AI-powered search.

## Features

- 📄 **Multi-format Document Support**: PDF, Markdown, TXT, HTML
- 🔍 **Advanced RAG System**: Hybrid retrieval with text and code chunking
- 🤖 **AI-Powered Queries**: Gemini AI integration for intelligent answers
- 📊 **Vector Database**: Qdrant for semantic search
- 💾 **Metadata Storage**: PostgreSQL for document and chunk metadata
- 🎨 **Modern UI**: React frontend with PDF viewer, text viewer, and query sidebar
- 🐳 **Dockerized**: Full Docker Compose setup for easy deployment
- 📱 **Responsive Design**: Resizable sidebar, code blocks, and improved text wrapping

## Tech Stack

### Backend
- **FastAPI**: Python web framework
- **PostgreSQL**: Relational database for metadata
- **Qdrant**: Vector database for embeddings
- **Gemini AI**: Google's Gemini for answer generation
- **Sentence Transformers**: Dual embedding models (text + code)
- **LangChain**: Text splitting and processing

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **React PDF**: PDF viewer
- **Lucide Icons**: Icon library

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd RAGDocs
   ```

2. **Start all services**
   ```bash
   docker compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development

#### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
RAGDocs/
├── app/                    # FastAPI backend
│   ├── api/                # API routes
│   ├── core/               # Core configuration
│   ├── models/             # Database models
│   └── services/           # Business logic
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   └── config.js       # API configuration
│   └── Dockerfile          # Frontend Docker build
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Backend Docker build
└── requirements.txt        # Python dependencies
```

## Configuration

### Environment Variables

#### Backend
- `POSTGRES_HOST`: PostgreSQL host (default: postgres)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_USER`: PostgreSQL user
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `QDRANT_HOST`: Qdrant host (default: qdrant)
- `QDRANT_PORT`: Qdrant port (default: 6333)
- `GEMINI_API_KEY`: Google Gemini API key
- `GEMINI_MODEL`: Gemini model name (default: gemini-2.5-flash)

#### Frontend
- `VITE_API_BASE_URL`: Backend API URL (default: http://localhost:8000)

## API Endpoints

- `POST /docs/upload`: Upload a document
- `POST /chat/query`: Query the RAG system
- `GET /docs/chunks/{doc_id}`: Get document chunks
- `DELETE /docs/documents/{doc_id}`: Delete a document
- `GET /health`: Health check

See full API documentation at http://localhost:8000/docs

## Features in Detail

### Document Processing
- Automatic file type detection
- Separate text and code chunking
- Heading extraction
- Language detection for code blocks

### Query Enhancement
- LLM-based query rewriting
- Multi-topic query support
- Keyword extraction
- Semantic search optimization

### Retrieval System
- Hybrid retrieval (text + code)
- Reranking for relevance
- Query caching (LFU)
- Multi-query support for complex questions

### Frontend Features
- PDF viewer with page navigation and zoom
- Text viewer for TXT, MD, HTML files
- Resizable query sidebar
- Code block rendering with syntax highlighting
- Responsive design

## Documentation

- [Frontend Setup Guide](FRONTEND_SETUP.md)
- [Document Types Guide](DOCUMENT_TYPES_GUIDE.md)
- [Gemini Setup Guide](GEMINI_SETUP.md)
- [Frontend Docker Guide](FRONTEND_DOCKER.md)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

[Add support information here]
