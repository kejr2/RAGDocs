# Frontend Quick Start

## Prerequisites

- Node.js 16+ installed
- Backend running at `http://localhost:8000`

## Step-by-Step

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies (First Time Only)

```bash
npm install
```

This will install:
- React 18
- Vite (build tool)
- Tailwind CSS
- Lucide React (icons)

### 3. Start Development Server

```bash
npm run dev
```

### 4. Open in Browser

The frontend will automatically open at:
**http://localhost:3000**

## Available Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Troubleshooting

### Port 3000 Already in Use

If port 3000 is taken, Vite will automatically use the next available port (3001, 3002, etc.)

### Cannot Connect to Backend

1. Make sure backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check API_BASE in `src/App.jsx`:
   ```javascript
   const API_BASE = 'http://localhost:8000';
   ```

### Module Not Found Errors

Reinstall dependencies:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Build Errors

Clear cache and rebuild:
```bash
rm -rf node_modules .vite dist
npm install
npm run build
```

## Production Build

To build for production:

```bash
npm run build
```

Output will be in `dist/` folder. You can serve it with any static file server:

```bash
npm run preview
# Or
npx serve dist
```

## Environment Variables

For production, you can use environment variables:

Create `.env` file:
```
VITE_API_BASE=http://localhost:8000
```

Then in `src/App.jsx`:
```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
```

## Quick Checklist

- [ ] Node.js installed (`node --version`)
- [ ] Backend running (`curl http://localhost:8000/health`)
- [ ] Dependencies installed (`npm install`)
- [ ] Development server running (`npm run dev`)
- [ ] Browser opened to http://localhost:3000

## Next Steps

1. Upload a document (PDF, HTML, Markdown, or text)
2. Ask questions about the document
3. View source citations

Enjoy! 🚀

