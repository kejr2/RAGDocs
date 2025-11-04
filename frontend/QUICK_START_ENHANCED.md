# Enhanced Frontend - Quick Start

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start the Frontend

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port Vite assigns)

### 3. Make Sure Backend is Running

```bash
# In another terminal, from project root
docker compose up -d
```

Backend should be running at `http://localhost:8000`

---

## ✨ New Features

### Three-Panel Layout

1. **Left Sidebar** - Document Management
   - Upload documents (PDF, Markdown, TXT, HTML)
   - View list of uploaded documents
   - Delete documents
   - See chunk counts (text/code)

2. **Center Panel** - PDF Viewer
   - Full PDF document viewing (when PDF is uploaded)
   - Page navigation (previous/next)
   - Zoom controls (zoom in/out)
   - Page counter
   - Responsive layout

3. **Right Sidebar** - Query Assistant
   - Chat interface for asking questions
   - Message history
   - Source citations
   - Show/Hide toggle button

### Design Improvements

- Modern gradient backgrounds
- Blue/indigo color scheme
- Smooth animations and transitions
- Custom scrollbars
- Enhanced shadows and borders
- Better spacing and typography
- Responsive design

---

## 📁 File Structure

```
frontend/
├── src/
│   ├── App.jsx              # Main app component
│   ├── components/
│   │   ├── PDFViewer.jsx    # PDF viewing component
│   │   └── QuerySidebar.jsx # Query chat sidebar
│   ├── index.css            # Enhanced styles
│   └── main.jsx             # Entry point
├── package.json
└── vite.config.js
```

---

## 🎯 Usage

1. **Upload a Document**
   - Click "Upload Document" in the left sidebar
   - Select a file (PDF, Markdown, TXT, HTML)
   - Wait for upload to complete

2. **View PDF** (if PDF uploaded)
   - PDF automatically displays in the center
   - Use arrow buttons to navigate pages
   - Use zoom controls to adjust size
   - Page counter shows current page

3. **Query the Document**
   - Type your question in the right sidebar
   - Press Enter or click Send
   - View AI-generated answers with sources
   - Continue the conversation

4. **Toggle Query Sidebar**
   - Click "Show/Hide Query" button in header
   - Sidebar can be collapsed for more PDF viewing space

---

## 🔧 Configuration

### API Base URL

If your backend is on a different port, update `API_BASE` in `src/App.jsx`:

```javascript
const API_BASE = 'http://localhost:8000';
```

### PDF Worker

The PDF viewer uses PDF.js worker. The worker path is automatically configured in `src/components/PDFViewer.jsx`.

---

## 🐛 Troubleshooting

### PDF Not Loading

1. Check browser console for errors
2. Ensure the file is a valid PDF
3. Check PDF.js worker is loading correctly

### Query Not Working

1. Verify backend is running: `curl http://localhost:8000/health`
2. Check browser console for API errors
3. Ensure document is uploaded and selected

### Styles Not Loading

1. Ensure Tailwind CSS is properly configured
2. Check `tailwind.config.js` exists
3. Verify `postcss.config.js` is set up

---

## 📝 Notes

- PDF viewing works for PDF files uploaded through the interface
- The PDF URL is created from the uploaded file blob
- For production, you might want to serve PDFs from the backend
- The query sidebar is collapsible for better PDF viewing experience

