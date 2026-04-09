import React, { useState, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize, AlignCenter } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.js',
    import.meta.url,
  ).toString();
}

export default function PDFViewer({ fileUrl, filename, darkMode }) {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pageInput, setPageInput] = useState('');
  const containerRef = useRef(null);
  const pageRef = useRef(null);

  function onDocumentLoadSuccess({ numPages }) {
    setNumPages(numPages);
    setLoading(false);
  }

  function onDocumentLoadError(err) {
    setError('Failed to load PDF');
    setLoading(false);
  }

  const goTo = (n) => setPageNumber(Math.max(1, Math.min(numPages || 1, n)));

  const handlePageInput = (e) => {
    const val = e.target.value;
    setPageInput(val);
    const n = parseInt(val, 10);
    if (!isNaN(n) && n >= 1 && numPages && n <= numPages) goTo(n);
  };

  const fitWidth = () => {
    if (!containerRef.current) return;
    const containerWidth = containerRef.current.clientWidth - 64;
    const pageWidthPt = 595; // A4 approx
    setScale(containerWidth / pageWidthPt);
  };

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) await containerRef.current?.requestFullscreen?.();
      else await document.exitFullscreen?.();
    } catch {
      // fullscreen not available or denied — ignore silently
    }
  };

  if (error) return (
    <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-base)' }}>
      <div className="text-center">
        <p className="font-medium mb-1" style={{ color: '#f87171' }}>Failed to load PDF</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{error}</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Controls bar */}
      <div className="px-4 py-2.5 border-b flex items-center gap-3 flex-shrink-0"
           style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>

        {/* Page nav */}
        <div className="flex items-center gap-1.5">
          <button onClick={() => goTo(pageNumber - 1)} disabled={pageNumber <= 1}
            className="p-1.5 rounded-lg disabled:opacity-30"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
            <ChevronLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-1">
            <input
              type="number"
              value={pageInput || pageNumber}
              min={1}
              max={numPages || 1}
              onChange={handlePageInput}
              onFocus={e => { setPageInput(''); e.target.select(); }}
              onBlur={() => setPageInput('')}
              className="w-10 text-center text-xs rounded-lg border outline-none py-1"
              style={{
                background: 'var(--bg-surface-2)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
            />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              / {numPages || '--'}
            </span>
          </div>

          <button onClick={() => goTo(pageNumber + 1)} disabled={!numPages || pageNumber >= numPages}
            className="p-1.5 rounded-lg disabled:opacity-30"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Divider */}
        <div className="w-px h-5" style={{ background: 'var(--border)' }} />

        {/* Zoom controls */}
        <div className="flex items-center gap-1.5">
          <button onClick={() => setScale(s => Math.max(0.4, +(s - 0.2).toFixed(1)))}
            className="p-1.5 rounded-lg"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs min-w-[44px] text-center"
                style={{ color: 'var(--text-secondary)' }}>
            {Math.round(scale * 100)}%
          </span>
          <button onClick={() => setScale(s => Math.min(3, +(s + 0.2).toFixed(1)))}
            className="p-1.5 rounded-lg"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>

        {/* Fit width */}
        <button onClick={fitWidth}
          className="p-1.5 rounded-lg" title="Fit to width"
          style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
          <AlignCenter className="w-4 h-4" />
        </button>

        {/* Fullscreen */}
        <button onClick={toggleFullscreen}
          className="p-1.5 rounded-lg" title="Fullscreen"
          style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
          <Maximize className="w-4 h-4" />
        </button>

        <span className="ml-auto text-xs truncate max-w-[200px]"
              style={{ color: 'var(--text-muted)' }}>
          {filename}
        </span>
      </div>

      {/* PDF Canvas */}
      <div ref={containerRef}
           className="flex-1 overflow-auto flex justify-center p-5 min-h-0"
           style={{ background: 'var(--bg-base)' }}>
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-t-[var(--accent)] rounded-full animate-spin mx-auto mb-3"
                   style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading PDF…</p>
            </div>
          </div>
        )}

        {fileUrl && (
          <div ref={pageRef}
               className="rounded-xl overflow-hidden shadow-xl"
               style={{ background: '#fff', display: loading ? 'none' : 'block' }}>
            <Document
              file={fileUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={null}
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
            </Document>
          </div>
        )}
      </div>
    </div>
  );
}
