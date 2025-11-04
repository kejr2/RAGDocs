# Enhanced Frontend Features

## New Features

### 1. Three-Panel Layout
- **Left Sidebar**: Document management (upload, list, delete)
- **Center Panel**: PDF viewer (when PDF is uploaded)
- **Right Sidebar**: Query assistant (chat interface)

### 2. PDF Viewer
- Full PDF document viewing
- Page navigation (previous/next)
- Zoom controls (zoom in/out)
- Page counter
- Responsive design

### 3. Improved Design
- Modern gradient backgrounds
- Better color scheme (blue/indigo theme)
- Smooth transitions and animations
- Enhanced shadows and borders
- Custom scrollbars
- Better spacing and typography

### 4. Query Sidebar
- Collapsible sidebar for queries
- Chat interface with message history
- Source citations
- Loading states
- Error handling

## Component Structure

```
src/
├── App.jsx              # Main app with layout
├── components/
│   ├── PDFViewer.jsx    # PDF viewing component
│   └── QuerySidebar.jsx # Query/chat sidebar
└── index.css            # Enhanced styles
```

## Usage

1. **Upload Document**: Click "Upload Document" in the left sidebar
2. **View PDF**: If it's a PDF, it will automatically display in the center
3. **Query**: Use the right sidebar to ask questions about the document
4. **Toggle Query Sidebar**: Click "Show/Hide Query" button in the header

## Dependencies Added

- `react-pdf`: React component for PDF rendering
- `pdfjs-dist`: PDF.js library for PDF parsing

## Notes

- PDF viewing works for PDF files uploaded through the interface
- The PDF URL is created from the uploaded file blob
- For production, you might want to serve PDFs from the backend

