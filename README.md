# RAGDocs - Advanced Code Documentation RAG System

<div align="center">

![RAGDocs Banner](banner-placeholder.png)

*A fully deployable, production-ready RAG (Retrieval Augmented Generation) system specifically designed for code documentation with intelligent hybrid retrieval and LLM-powered query enhancement.*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-FF6B6B?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## 🎯 Project Overview

**RAGDocs** is a production-ready, fully deployable RAG system engineered specifically for code documentation. It leverages **dual embedding models** (separate models for code and text), **LLM-powered query enhancement**, **hybrid retrieval**, and **intelligent reranking** to provide highly accurate and contextually relevant answers.

### Key Achievements

✨ **Dual Embedding Architecture**: Specialized models for code (`jinaai/jina-embeddings-v2-base-code`) and text (`all-MiniLM-L6-v2`)  
✨ **LLM-Powered Query Enhancement**: Gemini AI analyzes queries to optimize vector search strategies  
✨ **Hybrid Retrieval System**: Intelligently merges results from multiple contexts (text + code)  
✨ **Advanced Reranking**: Multi-factor relevance scoring with keyword overlap and type boosting  
✨ **Production-Ready**: Fully containerized with Docker Compose, ready for deployment  
✨ **Modern UI**: React-based interface with PDF viewer, code blocks, and resizable sidebar  

---

## 🏗️ Architecture Highlights

### Dual Embedding Models
- **Text Embeddings**: `all-MiniLM-L6-v2` for documentation and prose
- **Code Embeddings**: `jinaai/jina-embeddings-v2-base-code` for code snippets
- **Intelligent Routing**: Automatically routes queries to appropriate embedding model

### LLM-Powered Query Enhancement
- **Query Analysis**: Gemini AI analyzes user queries to extract:
  - Enhanced query variants
  - Keywords and synonyms
  - Query type (definition, how-to, example, multi-step)
  - Required topics for multi-query retrieval
- **Dynamic Search Strategy**: LLM determines optimal search parameters (top_k, multi-query needs)

### Hybrid Retrieval System
- **Multi-Context Merging**: Intelligently combines results from:
  - Text chunks (documentation)
  - Code chunks (snippets and examples)
- **Context-Aware Reranking**: Multi-factor scoring:
  - Semantic similarity scores
  - Keyword overlap
  - Type matching (code vs text)
  - Heading relevance
  - Language-specific prioritization

### Advanced Features
- **Query Caching**: LFU cache for frequently asked questions
- **Multi-Topic Queries**: Handles complex queries requiring multiple contexts
- **Language Detection**: Prioritizes code in requested language (Node.js, Python, etc.)
- **Error Handling**: Robust error handling with fallback mechanisms

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd RAGDocs

# Start all services
docker compose up -d
```

### Access Points
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Metadata storage for documents and chunks
- **Qdrant** - Vector database for semantic search
- **Gemini AI** - Query enhancement and answer generation
- **Sentence Transformers** - Dual embedding models
- **LangChain** - Text processing and chunking

### Frontend
- **React** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React PDF** - PDF viewer
- **Lucide Icons** - Icon library

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Static file serving and API proxying

---

## 📊 System Architecture

```
┌─────────────────┐
│   Frontend      │
│   (React)       │
│   Port: 3000     │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│   Backend       │
│   (FastAPI)     │
│   Port: 8000    │
└───┬──────────┬──┘
    │          │
    │          │
┌───▼───┐  ┌──▼────┐
│ Post  │  │Qdrant │
│ greSQL│  │Vector │
│       │  │  DB   │
└───────┘  └───────┘
```

---

## 🔑 Key Features

### Document Processing
- ✅ **Multi-format Support**: PDF, Markdown, TXT, HTML
- ✅ **Intelligent Chunking**: Separate text and code chunks
- ✅ **Heading Extraction**: Preserves document structure
- ✅ **Language Detection**: Identifies code language

### Query System
- ✅ **LLM Query Enhancement**: Optimizes queries before vector search
- ✅ **Multi-Query Support**: Handles complex, multi-topic queries
- ✅ **Hybrid Retrieval**: Searches both text and code collections
- ✅ **Smart Reranking**: Multi-factor relevance scoring

### User Interface
- ✅ **PDF Viewer**: Full PDF viewing with navigation and zoom
- ✅ **Text Viewer**: Markdown and code rendering
- ✅ **Resizable Sidebar**: Adjustable query interface
- ✅ **Code Blocks**: Syntax-highlighted code snippets
- ✅ **Responsive Design**: Works on all screen sizes

---

## 📁 Project Structure

```
RAGDocs/
├── app/                    # FastAPI backend
│   ├── api/                # API routes
│   │   ├── chat.py         # Query endpoint
│   │   ├── docs.py         # Document upload
│   │   └── debug.py        # Debug endpoints
│   ├── core/               # Core configuration
│   │   ├── database.py     # PostgreSQL connection
│   │   └── qdrant_client.py # Qdrant connection
│   ├── models/             # Database models
│   └── services/           # Business logic
│       ├── embeddings.py   # Dual embedding models
│       ├── query_enhancer.py # LLM query enhancement
│       ├── retrieval.py    # Hybrid retrieval
│       └── gemini.py       # Gemini AI integration
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   └── config.js      # API configuration
│   └── Dockerfile          # Frontend Docker build
├── docker-compose.yml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

---

## 🎓 Learning Outcomes

### Technical Skills Demonstrated
- **RAG System Design**: Understanding of retrieval-augmented generation architecture
- **Vector Databases**: Working with Qdrant for semantic search
- **Dual Embeddings**: Specialized models for different content types
- **LLM Integration**: Using Gemini AI for query enhancement
- **Full-Stack Development**: React frontend + FastAPI backend
- **Docker**: Containerization and orchestration
- **Database Design**: PostgreSQL schema design

### Advanced Concepts
- **Hybrid Retrieval**: Combining multiple search strategies
- **Query Enhancement**: Using LLMs to improve search quality
- **Reranking**: Multi-factor relevance scoring
- **Context Merging**: Intelligently combining multiple contexts
- **Production Deployment**: Docker Compose setup

---

## 📸 Screenshots

<div align="center">

![Application Screenshot](screenshot-placeholder.png)

*Screenshot of the RAGDocs application interface*

</div>

---

## 🔧 Configuration

### Environment Variables

#### Backend
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=ragdocs
POSTGRES_PASSWORD=ragdocs_password
POSTGRES_DB=ragdocs_db
QDRANT_HOST=qdrant
QDRANT_PORT=6333
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
```

#### Frontend
```bash
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📚 API Documentation

Full API documentation available at: http://localhost:8000/docs

### Key Endpoints
- `POST /docs/upload` - Upload a document
- `POST /chat/query` - Query the RAG system
- `GET /docs/chunks/{doc_id}` - Get document chunks
- `DELETE /docs/documents/{doc_id}` - Delete a document

---

## 🚧 Development

### Backend Development
```bash
cd app
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

---

## 📝 Documentation

- [Frontend Setup Guide](FRONTEND_SETUP.md)
- [Document Types Guide](DOCUMENT_TYPES_GUIDE.md)
- [Gemini Setup Guide](GEMINI_SETUP.md)
- [Frontend Docker Guide](FRONTEND_DOCKER.md)

---

## 🎯 Future Enhancements

- [ ] Support for more document formats (DOCX, PPTX)
- [ ] Multi-user support with authentication
- [ ] Advanced analytics and query tracking
- [ ] WebSocket support for real-time updates
- [ ] Multi-language code support expansion

---


## 👤 Author

**Aditya Kejriwal**

---

<div align="center">

**Built with ❤️ using FastAPI, React, and Gemini AI**

⭐ Star this repo if you found it helpful!

</div>
