# RAGDocs Frontend

Beautiful, modern frontend for the RAGDocs AI Documentation Assistant.

## Features

- 📄 **Document Upload** - Upload PDF, HTML, Markdown, and text files
- 💬 **AI Chat Interface** - Ask questions about your documents
- 📊 **Source Citations** - See where answers come from with relevance scores
- 🗂️ **Document Management** - View, select, and delete uploaded documents
- 🎨 **Modern UI** - Beautiful gradient design with Tailwind CSS
- ⚡ **Fast** - Built with Vite for lightning-fast development

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js 16+ installed
- Backend API running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
# Build the app
npm run build

# Preview production build
npm run preview
```

## Configuration

To change the API endpoint, edit `src/App.jsx`:

```javascript
const API_BASE = 'http://localhost:8000';
```

For production, use environment variables:

```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
```

And create a `.env` file:

```
VITE_API_BASE=https://your-api-domain.com
```

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx          # Main application component
│   ├── main.jsx         # React entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.js       # Vite configuration
└── tailwind.config.js   # Tailwind configuration
```

## API Endpoints Used

- `POST /docs/upload` - Upload document
- `POST /chat/query` - Query documents
- `DELETE /docs/documents/{doc_id}` - Delete document

For complete API documentation, see `../API_DOCUMENTATION.md`

## Features in Detail

### Document Upload
- Drag and drop or click to upload
- Supports PDF, HTML, Markdown, and text files
- Shows upload progress and status
- Displays chunk count (text + code)

### Chat Interface
- Clean message bubbles
- Real-time querying
- Source citations with relevance scores
- Code vs text chunk indicators
- Loading states

### Document Management
- Sidebar with all uploaded documents
- Document selection
- Delete functionality
- Chunk statistics

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Troubleshooting

### CORS Errors
Make sure the backend CORS is configured to allow your frontend origin.

### API Connection Issues
Verify the backend is running at `http://localhost:8000`:
```bash
curl http://localhost:8000/health
```

### Build Errors
Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

## License

Part of the RAGDocs project.




