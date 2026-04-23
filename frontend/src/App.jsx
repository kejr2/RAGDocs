import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Upload, FileText, Trash2, Loader, Book, MessageSquare,
  Search, SortAsc, Globe, FileCode, BarChart2
} from 'lucide-react';

// ╔══════════════════════════════════════════════════════╗
// ║  Built with ❤️  by Aditya Kejriwal                   ║
// ║  Try: ↑ ↑ ↓ ↓ ← → ← → B A                          ║
// ╚══════════════════════════════════════════════════════╝
const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];

function EasterEgg({ onClose }) {
  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center"
         style={{ background: 'rgba(0,0,0,0.85)' }}
         onClick={onClose}>
      <div className="relative text-center p-10 rounded-2xl border max-w-sm w-full mx-4 animate-fade-in"
           style={{ background: 'var(--bg-surface)', borderColor: 'var(--accent)' }}
           onClick={e => e.stopPropagation()}>
        <div className="text-5xl mb-4">🚀</div>
        <h2 className="text-2xl font-bold mb-1" style={{ color: 'var(--accent)' }}>
          Hey, you found me!
        </h2>
        <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
          Built with love by
        </p>
        <p className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          Aditya Kejriwal
        </p>
        <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
          github.com/kejr2
        </p>
        <div className="text-xs px-3 py-1.5 rounded-full inline-block mb-6"
             style={{ background: 'var(--bg-surface-2)', color: 'var(--text-muted)' }}>
          ↑ ↑ ↓ ↓ ← → ← → B A
        </div>
        <div>
          <button onClick={onClose}
            className="px-6 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: 'var(--accent)' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
import { useDropzone } from 'react-dropzone';
import toast, { Toaster } from 'react-hot-toast';
import PDFViewer from './components/PDFViewer';
import TextViewer from './components/TextViewer';
import QuerySidebar from './components/QuerySidebar';
import MetricsPage from './pages/MetricsPage';
import { API_BASE } from './config';

const ACCEPT_TYPES = { 'application/pdf': ['.pdf'], 'text/*': ['.md', '.txt', '.html', '.htm'] };
const ACCEPT_STRING = '.pdf,.md,.txt,.html,.htm';

function getFileIcon(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf')              return <FileText className="w-3.5 h-3.5" style={{ color: '#f87171' }} />;
  if (ext === 'html' || ext === 'htm') return <Globe   className="w-3.5 h-3.5" style={{ color: '#fb923c' }} />;
  if (ext === 'md')               return <FileCode className="w-3.5 h-3.5" style={{ color: '#60a5fa' }} />;
  return <FileText className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />;
}

export default function RAGDocsApp() {
  const [page,            setPage]            = useState('home');  // 'home' | 'metrics'
  const [documents,       setDocuments]       = useState([]);
  const [currentDoc,      setCurrentDoc]      = useState(null);
  const [uploadingFiles,  setUploadingFiles]  = useState({});
  const [showChat,        setShowChat]        = useState(true);
  const [pdfUrl,          setPdfUrl]          = useState(null);
  const [textContent,     setTextContent]     = useState(null);
  const [textFilename,    setTextFilename]    = useState(null);
  const [searchQuery,     setSearchQuery]     = useState('');
  const [sortBy,          setSortBy]          = useState('date');
  const [deleteConfirm,   setDeleteConfirm]   = useState(null);
  const [zoneHovered,     setZoneHovered]     = useState(false);
  const [pdfJumpTarget,   setPdfJumpTarget]   = useState(null);
  const [showEasterEgg,   setShowEasterEgg]   = useState(false);
  const konamiProgress = useRef(0);
  const fileInputRef = useRef(null);

  /* ─── Konami code easter egg ────────────────────────────────────────── */
  useEffect(() => {
    const handler = (e) => {
      if (e.key === KONAMI[konamiProgress.current]) {
        konamiProgress.current += 1;
        if (konamiProgress.current === KONAMI.length) {
          konamiProgress.current = 0;
          setShowEasterEgg(true);
        }
      } else {
        konamiProgress.current = e.key === KONAMI[0] ? 1 : 0;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  /* ─── Load indexed documents on mount ───────────────────────────────── */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/docs/documents`);
        if (!res.ok) return;
        const list = await res.json();
        if (cancelled || !Array.isArray(list)) return;
        setDocuments(list);
      } catch {
        /* silent — empty list is fine */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  /* ─── Upload ────────────────────────────────────────────────────────── */
  const uploadFile = useCallback(async (file) => {
    const key = file.name + Date.now();
    setUploadingFiles(prev => ({ ...prev, [key]: true }));

    if (file.type === 'application/pdf') {
      setPdfUrl(URL.createObjectURL(file));
      setTextContent(null);
    } else {
      setPdfUrl(null);
      const reader = new FileReader();
      reader.onload = e => { setTextContent(e.target.result); setTextFilename(file.name); };
      reader.readAsText(file);
    }

    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/docs/upload`, { method: 'POST', body: form });
      if (!res.ok) {
        let msg = 'Upload failed';
        try { msg = (await res.json()).detail || msg; } catch (_e) { /* ignore parse error */ }
        throw new Error(msg);
      }
      const result = await res.json();
      const doc = { ...result, uploadedAt: new Date().toISOString() };
      setDocuments(prev => prev.find(d => d.doc_id === result.doc_id) ? prev : [doc, ...prev]);
      setCurrentDoc(doc);
      if (result.status === 'already_exists') {
        toast(`"${result.filename}" already indexed`, { icon: 'ℹ️' });
      } else {
        toast.success(`"${result.filename}" — ${result.total_chunks} chunks indexed`);
      }
    } catch (err) {
      toast.error(`Failed: ${err.message || 'Upload failed'}`);
      setPdfUrl(null); setTextContent(null);
    } finally {
      setUploadingFiles(prev => { const n = { ...prev }; delete n[key]; return n; });
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, []);

  const onDrop = useCallback(files => files.forEach(uploadFile), [uploadFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPT_TYPES, noClick: true, multiple: true,
  });

  /* ─── Delete ────────────────────────────────────────────────────────── */
  const handleDelete = async (docId) => {
    try {
      const res = await fetch(`${API_BASE}/docs/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      setDocuments(prev => prev.filter(d => d.doc_id !== docId));
      if (currentDoc?.doc_id === docId) {
        setCurrentDoc(null); setPdfUrl(null); setTextContent(null); setTextFilename(null);
      }
      toast.success('Document deleted');
    } catch { toast.error('Failed to delete'); }
    finally { setDeleteConfirm(null); }
  };

  const isUploading = Object.keys(uploadingFiles).length > 0;
  const zoneActive  = isDragActive || zoneHovered;

  const filteredDocs = documents
    .filter(d => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'name')   return a.filename.localeCompare(b.filename);
      if (sortBy === 'chunks') return b.total_chunks - a.total_chunks;
      return new Date(b.uploadedAt || 0) - new Date(a.uploadedAt || 0);
    });

  /* ─── Render ────────────────────────────────────────────────────────── */
  return (
    <div className="h-screen flex flex-col overflow-hidden"
         style={{ background: 'var(--bg-app)', color: 'var(--text-primary)' }}>
      {showEasterEgg && <EasterEgg onClose={() => setShowEasterEgg(false)} />}

      <Toaster position="bottom-right" toastOptions={{
        style: {
          background: '#1a1a1a', color: '#e8e4de',
          border: '1px solid #2a2a2a', borderRadius: '10px', fontSize: '13px',
        },
      }} />

      {/* ══ Global Branding Header (44px) ══════════════════════════════════ */}
      <header className="flex items-center justify-between px-5 flex-shrink-0"
              style={{ height: '44px', background: '#0a0a0a', borderBottom: '1px solid #1e1e1e' }}>

        {/* Brand + nav links + current doc crumb */}
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => setPage('home')}
            className="font-brand select-none"
            style={{ fontSize: '18px', color: 'var(--volt)', letterSpacing: '3px', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            RAGDOCS
          </button>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage('home')}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono-ui transition-all"
              style={{
                background: page === 'home' ? 'rgba(198,241,53,0.08)' : 'transparent',
                color:      page === 'home' ? 'var(--volt)'           : 'var(--text-muted)',
              }}
            >
              <Book className="w-3 h-3" />
              Docs
            </button>
            <button
              onClick={() => setPage('metrics')}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono-ui transition-all"
              style={{
                background: page === 'metrics' ? 'rgba(198,241,53,0.08)' : 'transparent',
                color:      page === 'metrics' ? 'var(--volt)'           : 'var(--text-muted)',
              }}
            >
              <BarChart2 className="w-3 h-3" />
              Metrics
            </button>
          </div>

          {/* Breadcrumb for active document */}
          {page === 'home' && currentDoc && (
            <>
              <span className="font-mono-ui text-xs" style={{ color: 'var(--text-faint)' }}>/</span>
              <span className="font-mono-ui text-xs truncate max-w-[200px]"
                    style={{ color: 'var(--text-muted)' }}>
                {currentDoc.filename}
              </span>
            </>
          )}
        </div>

        {/* Status + chat toggle (only shown on home page) */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="flex items-center gap-1.5 font-mono-ui text-xs select-none"
                style={{ color: '#4ade80' }}>
            <span className="animate-volt-pulse text-base leading-none">●</span>
            <span>Live</span>
          </span>

          {page === 'home' && (
            <button
              onClick={() => setShowChat(s => !s)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono-ui transition-all"
              style={{
                background:   showChat ? 'var(--volt-dim)'    : 'transparent',
                color:        showChat ? 'var(--volt)'        : 'var(--text-muted)',
                border: `1px solid ${showChat ? 'var(--volt-border)' : 'var(--border)'}`,
              }}
            >
              <MessageSquare className="w-3 h-3" />
              Chat
            </button>
          )}
        </div>
      </header>

      {/* ══ Metrics page ══════════════════════════════════════════════════ */}
      {page === 'metrics' && (
        <MetricsPage />
      )}

      {/* ══ 3-Panel Content Row (home page) ════════════════════════════════ */}
      {page === 'home' && <div className="flex flex-1 overflow-hidden min-h-0">

        {/* ── Left Sidebar (260px) ──────────────────────────────────────── */}
        <aside className="flex flex-col h-full flex-shrink-0 border-r"
               style={{ width: '260px', background: 'var(--bg-sidebar)', borderColor: 'var(--border)' }}>

          {/* Upload zone */}
          <div
            {...getRootProps()}
            className="mx-3 mt-3 rounded-xl border-2 border-dashed p-4 text-center cursor-pointer transition-all duration-150"
            style={{
              borderColor: zoneActive ? 'var(--volt)' : 'var(--border-card)',
              background:  zoneActive ? 'var(--volt-glow)' : 'var(--bg-card)',
            }}
            onClick={() => fileInputRef.current?.click()}
            onMouseEnter={() => setZoneHovered(true)}
            onMouseLeave={() => setZoneHovered(false)}
          >
            <input {...getInputProps()} />
            <input ref={fileInputRef} type="file" multiple accept={ACCEPT_STRING}
                   className="hidden" onChange={e => Array.from(e.target.files || []).forEach(uploadFile)} />

            {isUploading ? (
              <div className="flex items-center justify-center gap-2 py-1">
                <Loader className="w-4 h-4 animate-spin" style={{ color: 'var(--volt)' }} />
                <span className="text-xs font-mono-ui" style={{ color: 'var(--volt)' }}>Uploading…</span>
              </div>
            ) : (
              <div className="py-1">
                <Upload className="w-5 h-5 mx-auto mb-1.5 transition-colors"
                        style={{ color: zoneActive ? 'var(--volt)' : 'var(--text-muted)' }} />
                <p className="text-xs font-mono-ui transition-colors"
                   style={{ color: zoneActive ? 'var(--volt)' : 'var(--text-secondary)' }}>
                  {isDragActive ? 'Drop to index' : 'Drop files or click'}
                </p>
                <p className="text-xs font-mono-ui mt-0.5" style={{ color: 'var(--text-faint)' }}>
                  PDF · MD · TXT · HTML
                </p>
              </div>
            )}
          </div>

          {/* Search + Sort */}
          <div className="px-3 pt-3 space-y-2 flex-shrink-0">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2"
                      style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search docs…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-7 pr-3 py-1.5 rounded-lg text-xs border outline-none"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              />
            </div>
            <div className="flex items-center gap-1">
              <SortAsc className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
              {['date', 'name', 'chunks'].map(s => (
                <button key={s} onClick={() => setSortBy(s)}
                  className="text-xs px-2 py-0.5 rounded-md capitalize font-mono-ui transition-all"
                  style={{
                    background: sortBy === s ? 'var(--volt)' : 'var(--bg-card)',
                    color:      sortBy === s ? '#000'        : 'var(--text-muted)',
                  }}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto px-3 pb-3 mt-3 min-h-0">
            <p className="text-xs font-mono-ui uppercase tracking-widest px-1 mb-2"
               style={{ color: 'var(--text-faint)' }}>
              {filteredDocs.length} doc{filteredDocs.length !== 1 ? 's' : ''}
            </p>

            {filteredDocs.length === 0 ? (
              <div className="text-center py-10">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-10" />
                <p className="text-xs font-mono-ui" style={{ color: 'var(--text-muted)' }}>
                  {searchQuery ? 'No matches' : 'No documents yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredDocs.map(doc => {
                  const isActive = currentDoc?.doc_id === doc.doc_id;
                  return (
                    <div key={doc.doc_id}
                      className="group rounded-lg px-2.5 py-2 cursor-pointer relative transition-all duration-150"
                      style={{
                        background:  isActive ? 'rgba(198,241,53,0.05)' : 'transparent',
                        borderLeft:  `3px solid ${isActive ? 'var(--volt)' : 'transparent'}`,
                      }}
                      onClick={() => setCurrentDoc(doc)}
                    >
                      <div className="flex items-center gap-2">
                        <div className="flex-shrink-0">{getFileIcon(doc.filename)}</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs truncate"
                             style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                            {doc.filename}
                          </p>
                          <p className="text-xs font-mono-ui mt-0.5" style={{ color: 'var(--text-faint)' }}>
                            {doc.total_chunks} chunks
                          </p>
                        </div>
                        <button
                          onClick={e => { e.stopPropagation(); setDeleteConfirm(doc.doc_id); }}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded transition-opacity"
                          style={{ color: 'var(--red)' }}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* ── Document Viewer (flex-1) ───────────────────────────────────── */}
        <main className="flex-1 overflow-hidden min-w-0 h-full"
              style={{ background: 'var(--bg-pdf)' }}>
          {currentDoc && pdfUrl ? (
            <PDFViewer fileUrl={pdfUrl} filename={currentDoc.filename} jumpTarget={pdfJumpTarget} />
          ) : currentDoc && textContent ? (
            <TextViewer fileContent={textContent} filename={textFilename || currentDoc.filename} darkMode={true} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-xs px-6">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5"
                     style={{ background: 'var(--volt-dim)', border: '1px solid var(--volt-border)' }}>
                  <Book className="w-7 h-7" style={{ color: 'var(--volt)' }} />
                </div>
                <h3 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                  {currentDoc ? 'Document indexed' : 'No document open'}
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {currentDoc
                    ? `"${currentDoc.filename}" is ready. Use the chat panel to query it.`
                    : 'Drop a document in the sidebar to get started.'}
                </p>
                {!currentDoc && (
                  <div className="flex flex-wrap gap-2 justify-center mt-4">
                    {['PDF', 'Markdown', 'HTML', 'TXT'].map(t => (
                      <span key={t} className="text-xs px-2.5 py-1 rounded-full font-mono-ui"
                            style={{ background: 'var(--bg-card)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        {/* ── Chat Sidebar (380px) ───────────────────────────────────────── */}
        {showChat && (
          <QuerySidebar
            currentDoc={currentDoc}
            isOpen={showChat}
            onClose={() => setShowChat(false)}
            darkMode={true}
            onJumpToPdf={(target) => setPdfJumpTarget(target)}
          />
        )}
      </div>}

      {/* ── Delete confirmation modal ──────────────────────────────────────── */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
             style={{ background: 'rgba(0,0,0,0.75)' }}
             onClick={() => setDeleteConfirm(null)}>
          <div className="rounded-2xl p-6 w-80 shadow-2xl animate-fade-in"
               style={{ background: 'var(--bg-card)', border: '1px solid var(--border-card)' }}
               onClick={e => e.stopPropagation()}>
            <h3 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Delete document?</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
              This removes the document and all indexed chunks. Cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg text-sm font-mono-ui"
                style={{ background: 'var(--bg-sidebar)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                Cancel
              </button>
              <button onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 rounded-lg text-sm font-mono-ui"
                style={{ background: 'var(--red-dim)', color: 'var(--red)', border: '1px solid var(--red-border)' }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
