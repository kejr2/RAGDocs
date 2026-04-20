import { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, AlignCenter, Maximize } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.js',
    import.meta.url,
  ).toString();
}

export default function PDFViewer({ fileUrl, filename, jumpTarget }) {
  const [numPages,     setNumPages]     = useState(null);
  const [currentPage,  setCurrentPage]  = useState(1);
  const [scale,        setScale]        = useState(1.2);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);
  const containerRef = useRef(null);
  const pageRefs     = useRef([]);

  /* ─── Document loaded ──────────────────────────────────────────────── */
  const onDocumentLoadSuccess = ({ numPages: n }) => {
    setNumPages(n);
    pageRefs.current = new Array(n).fill(null);
    setLoading(false);
  };

  const onDocumentLoadError = () => {
    setError('Failed to load PDF');
    setLoading(false);
  };

  /* ─── Navigate by scroll ───────────────────────────────────────────── */
  const scrollToPage = (n) => {
    const target = Math.max(1, Math.min(numPages || 1, n));
    setCurrentPage(target);
    const el = pageRefs.current[target - 1];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  /* ─── Track visible page while scrolling ──────────────────────────── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !numPages) return;

    const handler = () => {
      const containerTop = container.getBoundingClientRect().top;
      for (let i = 0; i < numPages; i++) {
        const el = pageRefs.current[i];
        if (!el) continue;
        const { bottom } = el.getBoundingClientRect();
        if (bottom > containerTop + 40) {
          setCurrentPage(i + 1);
          break;
        }
      }
    };

    container.addEventListener('scroll', handler, { passive: true });
    return () => container.removeEventListener('scroll', handler);
  }, [numPages]);

  /* ─── Jump to page from citation click ────────────────────────────── */
  useEffect(() => {
    if (!jumpTarget || !jumpTarget.ts) return;
    const page = jumpTarget.page;
    if (!page || page < 1) return;
    const clamped = Math.max(1, Math.min(numPages || 1, page));
    scrollToPage(clamped);

    // Flash the page with volt-green outline
    const el = pageRefs.current[clamped - 1];
    if (el) {
      el.classList.remove('pdf-page-flash');
      // Force reflow so re-adding the class re-triggers the animation
      void el.offsetWidth;
      el.classList.add('pdf-page-flash');
      setTimeout(() => el.classList.remove('pdf-page-flash'), 950);
    }
  }, [jumpTarget?.ts]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ─── Fit width ────────────────────────────────────────────────────── */
  const fitWidth = () => {
    if (!containerRef.current) return;
    const w = containerRef.current.clientWidth - 48;
    setScale(+(w / 595).toFixed(2));
  };

  /* ─── Fullscreen ───────────────────────────────────────────────────── */
  const toggleFullscreen = async () => {
    if (!document.fullscreenElement) {
      await containerRef.current?.requestFullscreen?.().catch(() => {});
    } else {
      await document.exitFullscreen?.().catch(() => {});
    }
  };

  /* ─── Error state ──────────────────────────────────────────────────── */
  if (error) return (
    <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-pdf)' }}>
      <div className="text-center">
        <p className="font-medium mb-1" style={{ color: 'var(--red)' }}>Failed to load PDF</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{error}</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: 'var(--bg-pdf)' }}>

      {/* ── Controls bar ─────────────────────────────────────────────── */}
      <div className="px-4 py-2 border-b flex items-center gap-2.5 flex-shrink-0"
           style={{ background: 'var(--bg-sidebar)', borderColor: 'var(--border)' }}>

        {/* Page navigation */}
        <div className="flex items-center gap-1">
          <button onClick={() => scrollToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg disabled:opacity-30 transition-opacity"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>

          <span className="text-xs font-mono-ui px-2 min-w-[64px] text-center"
                style={{ color: 'var(--text-secondary)' }}>
            {currentPage}
            <span style={{ color: 'var(--text-faint)' }}> / {numPages || '–'}</span>
          </span>

          <button onClick={() => scrollToPage(currentPage + 1)}
            disabled={!numPages || currentPage >= numPages}
            className="p-1.5 rounded-lg disabled:opacity-30 transition-opacity"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="w-px h-4 flex-shrink-0" style={{ background: 'var(--border)' }} />

        {/* Zoom */}
        <div className="flex items-center gap-1">
          <button onClick={() => setScale(s => Math.max(0.4, +(s - 0.15).toFixed(2)))}
            className="p-1.5 rounded-lg"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs font-mono-ui min-w-[42px] text-center"
                style={{ color: 'var(--text-secondary)' }}>
            {Math.round(scale * 100)}%
          </span>
          <button onClick={() => setScale(s => Math.min(3.0, +(s + 0.15).toFixed(2)))}
            className="p-1.5 rounded-lg"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Fit width */}
        <button onClick={fitWidth} title="Fit to width"
          className="p-1.5 rounded-lg"
          style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
          <AlignCenter className="w-3.5 h-3.5" />
        </button>

        {/* Fullscreen */}
        <button onClick={toggleFullscreen} title="Fullscreen"
          className="p-1.5 rounded-lg"
          style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
          <Maximize className="w-3.5 h-3.5" />
        </button>

        <span className="ml-auto text-xs font-mono-ui truncate max-w-[200px]"
              style={{ color: 'var(--text-muted)' }}>
          {filename}
        </span>
      </div>

      {/* ── All pages stacked ─────────────────────────────────────────── */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto min-h-0"
        style={{ background: 'var(--bg-pdf)' }}
      >
        {/* Loading spinner */}
        {loading && (
          <div className="flex items-center justify-center py-24">
            <div className="text-center">
              <div className="w-10 h-10 border-2 rounded-full animate-spin mx-auto mb-3"
                   style={{ borderColor: 'var(--border)', borderTopColor: 'var(--volt)' }} />
              <p className="text-sm font-mono-ui" style={{ color: 'var(--text-muted)' }}>Loading PDF…</p>
            </div>
          </div>
        )}

        {fileUrl && (
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={null}
            className="flex flex-col items-center py-6 gap-4"
          >
            {numPages && Array.from({ length: numPages }, (_, i) => (
              <div
                key={i + 1}
                ref={el => { pageRefs.current[i] = el; }}
                className="flex-shrink-0 shadow-2xl"
                style={{ display: loading ? 'none' : 'block' }}
              >
                <Page
                  pageNumber={i + 1}
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
              </div>
            ))}
          </Document>
        )}
      </div>
    </div>
  );
}
