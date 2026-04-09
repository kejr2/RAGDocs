import React, { useState, useRef, useCallback } from 'react';
import {
  Upload, FileText, Code, Trash2, Loader, Book, MessageSquare,
  Sun, Moon, Search, SortAsc, Globe, FileCode, ChevronDown, X
} from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import toast, { Toaster } from 'react-hot-toast';
import PDFViewer from './components/PDFViewer';
import TextViewer from './components/TextViewer';
import QuerySidebar from './components/QuerySidebar';
import { API_BASE } from './config';

const ACCEPT_TYPES = { 'application/pdf': ['.pdf'], 'text/*': ['.md', '.txt', '.html', '.htm'] };
const ACCEPT_STRING = '.pdf,.md,.txt,.html,.htm';

function getFileIcon(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return <FileText className="w-4 h-4 text-red-400" />;
  if (ext === 'html' || ext === 'htm') return <Globe className="w-4 h-4 text-orange-400" />;
  if (ext === 'md') return <FileCode className="w-4 h-4 text-blue-400" />;
  return <FileText className="w-4 h-4 text-slate-400" />;
}

function getFileTypeBadge(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  const map = { pdf: 'bg-red-500/20 text-red-300', md: 'bg-blue-500/20 text-blue-300', html: 'bg-orange-500/20 text-orange-300', htm: 'bg-orange-500/20 text-orange-300', txt: 'bg-slate-500/20 text-slate-300' };
  return { cls: map[ext] || 'bg-slate-500/20 text-slate-300', label: ext?.toUpperCase() || 'FILE' };
}

export default function RAGDocsApp() {
  const [documents, setDocuments] = useState([]);
  const [currentDoc, setCurrentDoc] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState({});
  const [showQuerySidebar, setShowQuerySidebar] = useState(true);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [textContent, setTextContent] = useState(null);
  const [textFilename, setTextFilename] = useState(null);
  const [darkMode, setDarkMode] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const fileInputRef = useRef(null);

  // Apply dark mode to html element
  React.useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const uploadFile = useCallback(async (file) => {
    const key = file.name + Date.now();
    setUploadingFiles(prev => ({ ...prev, [key]: true }));

    // Prepare viewer content immediately
    if (file.type === 'application/pdf') {
      setPdfUrl(URL.createObjectURL(file));
      setTextContent(null);
    } else {
      setPdfUrl(null);
      const reader = new FileReader();
      reader.onload = (e) => { setTextContent(e.target.result); setTextFilename(file.name); };
      reader.readAsText(file);
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/docs/upload`, { method: 'POST', body: formData });
      if (!response.ok) {
        let errMsg = 'Upload failed';
        try { errMsg = (await response.json()).detail || errMsg; } catch {}
        throw new Error(errMsg);
      }
      const result = await response.json();
      const docWithDate = { ...result, uploadedAt: new Date().toISOString() };
      setDocuments(prev => {
        if (prev.find(d => d.doc_id === result.doc_id)) return prev;
        return [docWithDate, ...prev];
      });
      setCurrentDoc(docWithDate);
      if (result.status === 'already_exists') {
        toast(`"${result.filename}" was already uploaded`, { icon: 'ℹ️' });
      } else {
        toast.success(`Uploaded "${result.filename}" — ${result.total_chunks} chunks`);
      }
    } catch (error) {
      toast.error(`Failed: ${error.message}`);
      setPdfUrl(null); setTextContent(null);
    } finally {
      setUploadingFiles(prev => { const n = { ...prev }; delete n[key]; return n; });
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, []);

  const onDrop = useCallback((acceptedFiles) => {
    acceptedFiles.forEach(uploadFile);
  }, [uploadFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT_TYPES,
    noClick: true,
    multiple: true,
  });

  const handleFileInput = (e) => {
    Array.from(e.target.files || []).forEach(uploadFile);
  };

  const handleDeleteDoc = async (docId) => {
    try {
      const response = await fetch(`${API_BASE}/docs/documents/${docId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Delete failed');
      setDocuments(prev => prev.filter(d => d.doc_id !== docId));
      if (currentDoc?.doc_id === docId) {
        setCurrentDoc(null); setPdfUrl(null); setTextContent(null); setTextFilename(null);
      }
      toast.success('Document deleted');
    } catch {
      toast.error('Failed to delete document');
    } finally {
      setShowDeleteConfirm(null);
    }
  };

  const handleDocSelect = (doc) => {
    setCurrentDoc(doc);
  };

  const isUploading = Object.keys(uploadingFiles).length > 0;

  // Filter + sort documents
  const filteredDocs = documents
    .filter(d => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'name') return a.filename.localeCompare(b.filename);
      if (sortBy === 'chunks') return b.total_chunks - a.total_chunks;
      return new Date(b.uploadedAt || 0) - new Date(a.uploadedAt || 0);
    });

  const surfaceCls = darkMode
    ? 'bg-surface border-[var(--border)]'
    : 'bg-white border-gray-200';

  return (
    <div className={`h-screen flex overflow-hidden ${darkMode ? 'dark' : ''}`}
         style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: darkMode ? '#1e293b' : '#fff',
            color: darkMode ? '#f1f5f9' : '#0f172a',
            border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
            borderRadius: '0.75rem',
            fontSize: '13px',
          },
        }}
      />

      {/* ── Left Sidebar ─────────────────────────────────────────────────── */}
      <div className="w-72 flex flex-col h-full flex-shrink-0 border-r"
           style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>

        {/* App Header */}
        <div className="px-4 py-4 border-b flex items-center justify-between flex-shrink-0"
             style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg" style={{ background: 'var(--accent-light)' }}>
              <Book className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h1 className="font-bold text-sm leading-tight" style={{ color: 'var(--text-primary)' }}>RAGDocs</h1>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>AI Doc Assistant</p>
            </div>
          </div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-1.5 rounded-lg hover:opacity-80"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}
            title="Toggle dark mode"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>

        {/* Upload Drop Zone */}
        <div
          {...getRootProps()}
          className={`mx-3 mt-3 rounded-xl border-2 border-dashed p-4 text-center cursor-pointer transition-all
            ${isDragActive ? 'drop-active' : ''}`}
          style={{
            borderColor: isDragActive ? 'var(--accent)' : 'var(--border-2)',
            background: isDragActive ? 'rgba(14,165,233,0.06)' : 'var(--bg-surface-2)'
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input {...getInputProps()} />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPT_STRING}
            className="hidden"
            onChange={handleFileInput}
          />
          {isUploading ? (
            <div className="flex items-center justify-center gap-2 py-1">
              <Loader className="w-4 h-4 animate-spin" style={{ color: 'var(--accent)' }} />
              <span className="text-sm" style={{ color: 'var(--accent)' }}>Uploading…</span>
            </div>
          ) : (
            <div className="py-1">
              <Upload className="w-5 h-5 mx-auto mb-1" style={{ color: 'var(--text-muted)' }} />
              <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                {isDragActive ? 'Drop files here' : 'Drop files or click to upload'}
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                PDF, MD, TXT, HTML
              </p>
            </div>
          )}
        </div>

        {/* Search + Sort */}
        <div className="px-3 pt-3 space-y-2 flex-shrink-0">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search documents…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs border outline-none focus:ring-1"
              style={{
                background: 'var(--bg-surface-2)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
                '--tw-ring-color': 'var(--accent)',
              }}
            />
          </div>
          <div className="flex items-center gap-1">
            <SortAsc className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
            {['date', 'name', 'chunks'].map(s => (
              <button key={s}
                onClick={() => setSortBy(s)}
                className="text-xs px-2 py-0.5 rounded-md capitalize"
                style={{
                  background: sortBy === s ? 'var(--accent)' : 'var(--bg-surface-2)',
                  color: sortBy === s ? '#fff' : 'var(--text-secondary)',
                }}
              >{s}</button>
            ))}
          </div>
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto px-3 pb-3 mt-2 min-h-0">
          <p className="text-xs font-semibold uppercase tracking-wide px-1 mb-2"
             style={{ color: 'var(--text-muted)' }}>
            {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''}
          </p>
          {filteredDocs.length === 0 ? (
            <div className="text-center py-10">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-20" />
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {searchQuery ? 'No matching documents' : 'No documents yet'}
              </p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {filteredDocs.map((doc) => {
                const badge = getFileTypeBadge(doc.filename);
                const isActive = currentDoc?.doc_id === doc.doc_id;
                return (
                  <div key={doc.doc_id}
                    className="group rounded-xl p-3 cursor-pointer relative border transition-all"
                    style={{
                      background: isActive ? 'var(--accent-light)' : 'var(--bg-surface-2)',
                      borderColor: isActive ? 'var(--accent)' : 'transparent',
                    }}
                    onClick={() => handleDocSelect(doc)}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex-shrink-0">{getFileIcon(doc.filename)}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                          {doc.filename}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${badge.cls}`}>
                            {badge.label}
                          </span>
                          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            {doc.total_chunks} chunks
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={e => { e.stopPropagation(); setShowDeleteConfirm(doc.doc_id); }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md flex-shrink-0"
                        style={{ color: '#f87171' }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Main Content ──────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Topbar */}
        <div className="px-5 py-3 border-b flex items-center justify-between flex-shrink-0"
             style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="min-w-0 flex-1">
            {currentDoc ? (
              <div>
                <p className="font-semibold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                  {currentDoc.filename}
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {currentDoc.total_chunks} chunks · {currentDoc.text_chunks} text · {currentDoc.code_chunks} code
                </p>
              </div>
            ) : (
              <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>RAGDocs</p>
            )}
          </div>
          <button
            onClick={() => setShowQuerySidebar(!showQuerySidebar)}
            className="ml-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
            style={{
              background: showQuerySidebar ? 'var(--accent)' : 'var(--bg-surface-2)',
              color: showQuerySidebar ? '#fff' : 'var(--text-secondary)',
            }}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            {showQuerySidebar ? 'Hide Chat' : 'Chat'}
          </button>
        </div>

        {/* Document View */}
        <div className="flex-1 overflow-hidden min-h-0">
          {currentDoc && pdfUrl ? (
            <PDFViewer fileUrl={pdfUrl} filename={currentDoc.filename} darkMode={darkMode} />
          ) : currentDoc && textContent ? (
            <TextViewer fileContent={textContent} filename={textFilename || currentDoc.filename} darkMode={darkMode} />
          ) : (
            <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-base)' }}>
              <div className="text-center max-w-sm px-6">
                <Book className="w-16 h-16 mx-auto mb-5 opacity-20" />
                <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                  {currentDoc ? 'Document Indexed' : 'Welcome to RAGDocs'}
                </h3>
                <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
                  {currentDoc
                    ? `"${currentDoc.filename}" is ready. Use the chat sidebar to query it.`
                    : 'Drop a document in the sidebar to get started. Supports PDF, Markdown, HTML, and TXT.'}
                </p>
                {!currentDoc && (
                  <div className="flex flex-wrap gap-2 justify-center">
                    {['PDF', 'Markdown', 'HTML', 'TXT'].map(t => (
                      <span key={t} className="text-xs px-2.5 py-1 rounded-full"
                            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Right Sidebar: Chat ───────────────────────────────────────────── */}
      {showQuerySidebar && (
        <QuerySidebar
          currentDoc={currentDoc}
          isOpen={showQuerySidebar}
          onClose={() => setShowQuerySidebar(false)}
          darkMode={darkMode}
        />
      )}

      {/* ── Delete Confirmation Modal ─────────────────────────────────────── */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
             style={{ background: 'rgba(0,0,0,0.5)' }}
             onClick={() => setShowDeleteConfirm(null)}>
          <div className="rounded-2xl p-6 w-80 shadow-2xl"
               style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
               onClick={e => e.stopPropagation()}>
            <h3 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Delete document?</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
              This will remove the document and all its indexed chunks. This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
                Cancel
              </button>
              <button onClick={() => handleDeleteDoc(showDeleteConfirm)}
                className="px-4 py-2 rounded-lg text-sm text-white"
                style={{ background: '#ef4444' }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
