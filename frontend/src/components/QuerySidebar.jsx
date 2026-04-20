import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, X, Code, FileText, Copy, Check, RotateCcw,
  Trash2, Clock, Zap, MessageSquare, ChevronDown, ChevronRight, Cpu,
  ThumbsUp, ThumbsDown, Shield
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import toast from 'react-hot-toast';
import { API_BASE } from '../config';

const HISTORY_KEY = 'ragdocs_query_history';
const MAX_HISTORY = 10;

const SUGGESTIONS = [
  'How do I get started?',
  'What are the main concepts?',
  'Show me a code example',
  'Explain the architecture',
];

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { return []; }
}
function saveHistory(h) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, MAX_HISTORY))); } catch (_e) { /* ignore */ }
}

/* ── Confidence badge ──────────────────────────────────────────────────────── */
function ConfidenceBadge({ confidence }) {
  if (!confidence) return null;
  const map = {
    HIGH:   { cls: 'badge-high',   icon: '●', label: 'High confidence'   },
    MEDIUM: { cls: 'badge-medium', icon: '◐', label: 'Medium confidence' },
    LOW:    { cls: 'badge-low',    icon: '○', label: 'Low confidence'    },
  };
  const { cls, icon, label } = map[confidence] || map.LOW;
  return (
    <span className={cls} title={label}>
      <span aria-hidden="true">{icon}</span>
      {confidence} CONFIDENCE
    </span>
  );
}

/* ── Source preview card ───────────────────────────────────────────────────── */
function SourceCard({ src, onJumpToPdf }) {
  const [hovered, setHovered] = useState(false);
  const preview = src.content?.slice(0, 220) || '';
  const pageNum = src.metadata?.page_number;
  const canJump = onJumpToPdf && pageNum && pageNum > 0;

  const handleClick = () => {
    if (!canJump) return;
    onJumpToPdf({
      page:    pageNum,
      chunkId: src.metadata?.chunk_id,
      start:   src.metadata?.start,
      end:     src.metadata?.end,
      ts:      Date.now(),
    });
  };

  return (
    <div className="relative">
      <div
        className="rounded-lg p-2.5 border text-xs transition-all"
        style={{
          background:   'var(--bg-app)',
          borderColor:  hovered && canJump ? 'var(--volt-border)' : 'var(--border)',
          cursor:       canJump ? 'pointer' : 'default',
          outline:      hovered && canJump ? '1px solid var(--volt-border)' : 'none',
        }}
        onClick={handleClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <div className="flex items-center gap-2">
          {src.metadata?.type === 'code'
            ? <Code     className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--volt)' }} />
            : <FileText className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />}
          <span className="font-mono-ui truncate flex-1" style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>
            {src.metadata?.heading || src.metadata?.source_file || 'Source'}
          </span>
          {pageNum > 0 && (
            <span className="flex-shrink-0 font-mono-ui text-xs px-1.5 py-0.5 rounded"
                  style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
              p.{pageNum}
            </span>
          )}
          <span className="flex-shrink-0 font-mono-ui text-xs px-1.5 py-0.5 rounded"
                style={{ background: 'var(--volt-dim)', color: 'var(--volt)', border: '1px solid var(--volt-border)' }}>
            {Math.round((src.relevance_score || 0) * 100)}%
          </span>
        </div>
      </div>

      {/* Hover preview */}
      {hovered && preview && (
        <div
          className="absolute z-50 bottom-full mb-2 left-0 right-0 rounded-xl p-3 text-xs shadow-2xl border"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--border-card)',
            color: 'var(--text-secondary)',
            lineHeight: '1.65',
            maxWidth: '360px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          <p className="font-semibold mb-1.5 font-mono-ui text-xs" style={{ color: 'var(--text-muted)' }}>
            {canJump ? 'CLICK TO JUMP · PREVIEW' : 'PREVIEW'}
          </p>
          {preview}{src.content?.length > 220 ? '…' : ''}
        </div>
      )}
    </div>
  );
}

/* ── Recursively extract plain text from React children (for copy button) ──── */
function extractText(node) {
  if (node == null) return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node?.props?.children !== undefined) return extractText(node.props.children);
  return '';
}

/* ── Code block with copy ──────────────────────────────────────────────────── */
function CodeBlock({ children, className }) {
  const [copied, setCopied] = useState(false);
  // extractText gives raw text for clipboard; render children directly so
  // rehype-highlight's syntax-coloured spans are preserved in the UI.
  const rawCode = extractText(children).replace(/\n$/, '');
  const lang = className?.replace('language-', '') || 'code';

  const copy = () => {
    navigator.clipboard.writeText(rawCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="relative my-2 rounded-xl overflow-hidden border"
         style={{ borderColor: 'var(--border-card)', background: '#0d0d0d' }}>
      <div className="flex items-center justify-between px-3 py-1.5"
           style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-xs font-mono-ui" style={{ color: 'var(--text-muted)' }}>{lang}</span>
        <button onClick={copy}
          className="flex items-center gap-1 text-xs px-2 py-0.5 rounded"
          style={{ color: copied ? '#4ade80' : 'var(--text-muted)', background: 'var(--bg-card)' }}>
          {copied
            ? <><Check className="w-3 h-3" /> Copied</>
            : <><Copy  className="w-3 h-3" /> Copy</>}
        </button>
      </div>
      <pre style={{ margin: 0, background: 'transparent', padding: '1rem' }}>
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

function MarkdownMessage({ content }) {
  return (
    <div className="prose-dark text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ inline, className, children, ...props }) {
            if (inline) return (
              <code {...props}>{children}</code>
            );
            return <CodeBlock className={className}>{children}</CodeBlock>;
          },
          pre({ children }) { return <>{children}</>; },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

/* ── Main Sidebar ──────────────────────────────────────────────────────────── */
export default function QuerySidebar({ currentDoc, onClose, onJumpToPdf }) {
  const [query,         setQuery]         = useState('');
  const [messages,      setMessages]      = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('ragdocs_messages') || '[]'); } catch { return []; }
  });
  const [streaming,     setStreaming]     = useState(false);
  const [sidebarWidth,  setSidebarWidth]  = useState(380);
  const [isResizing,    setIsResizing]    = useState(false);
  const [history,       setHistory]       = useState(loadHistory);
  const [showHistory,   setShowHistory]   = useState(false);
  const [copiedMsg,     setCopiedMsg]     = useState(null);
  const [models,        setModels]        = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef    = useRef(null);
  const abortRef       = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    try { sessionStorage.setItem('ragdocs_messages', JSON.stringify(messages)); } catch (_e) { /* ignore */ }
  }, [messages]);

  useEffect(() => {
    fetch(`${API_BASE}/chat/models`)
      .then(r => r.json())
      .then(data => {
        if (data.models) {
          setModels(data.models);
          setSelectedModel(data.default || data.models[0]?.id || '');
        }
      })
      .catch(() => {});
  }, []);

  const addToHistory = useCallback((q) => {
    setHistory(prev => {
      const next = [q, ...prev.filter(h => h !== q)].slice(0, MAX_HISTORY);
      saveHistory(next);
      return next;
    });
  }, []);

  /* ─── Send query ─────────────────────────────────────────────────────── */
  const sendQuery = useCallback(async (queryText) => {
    const q = (queryText || query).trim();
    if (!q || streaming) return;

    setQuery('');
    setShowHistory(false);
    addToHistory(q);

    const userMsg = { id: crypto.randomUUID(), role: 'user', content: q };
    const assistantMsg = {
      id: crypto.randomUUID(), role: 'assistant', content: '',
      streaming: true, sources: [], confidence: null, fallback_triggered: false,
    };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current  = controller;
    const timeoutId   = setTimeout(() => controller.abort(), 60000);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          doc_id: currentDoc?.doc_id || null,
          top_k: 8,
          model: selectedModel || null,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        if (response.status === 400) {
          let detail = 'Query blocked by safety guard.';
          try { const j = await response.json(); detail = j.detail || detail; } catch (_) { /* ignore */ }
          toast.error(detail);
          setMessages(prev => prev.slice(0, -2)); // remove pending user+assistant msgs
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = '';

      const processLines = () => {
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          try {
            const data = JSON.parse(line.replace(/^data:\s*/, ''));
            if (data.token !== undefined) {
              setMessages(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === 'assistant') {
                  next[next.length - 1] = { ...last, content: last.content + data.token };
                }
                return next;
              });
            } else if (data.done) {
              setMessages(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === 'assistant') {
                  next[next.length - 1] = {
                    ...last,
                    streaming: false,
                    sources: data.sources || [],
                    confidence: data.confidence || null,
                    fallback_triggered: data.fallback_triggered || false,
                    query_id: data.query_id || null,
                    feedback: null,
                  };
                }
                return next;
              });
            } else if (data.error) {
              throw new Error(data.error);
            }
          } catch (_e) { /* skip malformed SSE */ }
        }
      };

      let streamDone = false;
      while (!streamDone) {
        const { done, value } = await reader.read();
        if (done) { streamDone = true; break; }
        buffer += decoder.decode(value, { stream: true });
        processLines();
      }
      buffer += decoder.decode();
      if (buffer.trim()) processLines();

    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === 'assistant' && last.streaming) {
            next[next.length - 1] = {
              ...last,
              content: last.content ? last.content + '\n\n_[Request timed out]_' : '_Request timed out_',
              streaming: false, isError: true,
            };
          }
          return next;
        });
        return;
      }
      // Fallback to non-streaming
      try {
        const res  = await fetch(`${API_BASE}/chat/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, doc_id: currentDoc?.doc_id || null, top_k: 8, model: selectedModel || null }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Query failed');
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1] = {
            role: 'assistant', content: data.answer,
            streaming: false, sources: data.sources || [],
            confidence: data.confidence || null,
            fallback_triggered: data.fallback_triggered || false,
          };
          return next;
        });
      } catch (fallbackErr) {
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1] = {
            role: 'assistant', content: `Error: ${fallbackErr.message}`,
            streaming: false, isError: true, sources: [],
          };
          return next;
        });
      }
    } finally {
      clearTimeout(timeoutId);
      setStreaming(false);
    }
  }, [query, streaming, currentDoc, addToHistory, selectedModel]);

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(); }
  };

  const handleRetry = () => {
    const lastUser = [...messages].reverse().find(m => m.role === 'user');
    if (lastUser) { setMessages(prev => prev.slice(0, -2)); sendQuery(lastUser.content); }
  };

  const copyMessage = (idx, content) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedMsg(idx); setTimeout(() => setCopiedMsg(null), 2000);
    });
  };

  const submitFeedback = useCallback(async (msgId, queryId, value) => {
    // Optimistically update UI
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, feedback: value } : m
    ));
    try {
      const res = await fetch(`${API_BASE}/chat/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_id: queryId, feedback: value }),
      });
      if (!res.ok) throw new Error('Feedback failed');
    } catch {
      // Roll back on failure
      setMessages(prev => prev.map(m =>
        m.id === msgId ? { ...m, feedback: null } : m
      ));
    }
  }, []);

  /* ─── Drag resize ────────────────────────────────────────────────────── */
  const startResize = e => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startW = sidebarWidth;
    const onMove = me => setSidebarWidth(Math.max(320, Math.min(800, startW + startX - me.clientX)));
    const onUp   = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup',   onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup',   onUp);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="relative flex flex-col h-full flex-shrink-0 border-l"
         style={{ width: sidebarWidth, background: 'var(--bg-chat)', borderColor: 'var(--border)' }}>

      {/* Resize handle */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10 transition-colors"
        style={{ background: isResizing ? 'var(--volt)' : 'transparent' }}
        onMouseDown={startResize}
        onMouseEnter={e  => { e.currentTarget.style.background = 'var(--volt-border)'; }}
        onMouseLeave={e  => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }}
      />

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0"
           style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquare className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--volt)' }} />
          <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>AI Assistant</span>
          {currentDoc && (
            <span className="text-xs font-mono-ui px-2 py-0.5 rounded-full max-w-[100px] truncate"
                  style={{ background: 'var(--volt-dim)', color: 'var(--volt)', border: '1px solid var(--volt-border)' }}>
              {currentDoc.filename}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {hasMessages && (
            <button onClick={() => setMessages([])}
              className="p-1.5 rounded-lg" title="Clear conversation"
              style={{ color: 'var(--text-muted)', background: 'var(--bg-card)' }}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button onClick={onClose} className="p-1.5 rounded-lg"
            style={{ color: 'var(--text-muted)', background: 'var(--bg-card)' }}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ─── Model selector ──────────────────────────────────────────────── */}
      {models.length > 0 && (
        <div className="px-3 pt-2 pb-1 flex items-center gap-2 flex-shrink-0">
          <Cpu className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
          <select
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
            className="flex-1 text-xs rounded-lg px-2 py-1 border outline-none font-mono-ui"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
          >
            {models.map(m => (
              <option key={m.id} value={m.id}>{m.name} ({m.tier})</option>
            ))}
          </select>
        </div>
      )}

      {/* ─── Recent questions ─────────────────────────────────────────────── */}
      {history.length > 0 && (
        <div className="px-3 pt-1 flex-shrink-0">
          <button
            onClick={() => setShowHistory(s => !s)}
            className="w-full flex items-center gap-1.5 text-xs py-1 px-1 rounded font-mono-ui"
            style={{ color: 'var(--text-muted)' }}
          >
            {showHistory
              ? <ChevronDown  className="w-3 h-3" />
              : <ChevronRight className="w-3 h-3" />}
            <Clock className="w-3 h-3" />
            Recent ({history.length})
          </button>
          {showHistory && (
            <div className="mt-1 mb-1 rounded-xl border overflow-hidden animate-fade-in"
                 style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <div className="max-h-40 overflow-y-auto">
                {history.map((h, i) => (
                  <button key={h}
                    onClick={() => { sendQuery(h); setShowHistory(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs truncate"
                    style={{
                      color:        'var(--text-secondary)',
                      borderBottom: i < history.length - 1 ? '1px solid var(--border)' : 'none',
                    }}>
                    {h}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Messages ────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 min-h-0">
        {!hasMessages ? (
          <div className="space-y-4 animate-fade-in">
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3"
                   style={{ background: 'var(--volt-dim)', border: '1px solid var(--volt-border)' }}>
                <Zap className="w-5 h-5" style={{ color: 'var(--volt)' }} />
              </div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                {currentDoc ? 'Ask anything about this document' : 'Upload a document to start'}
              </p>
              <p className="text-xs mt-1 font-mono-ui" style={{ color: 'var(--text-muted)' }}>
                Streaming · BM25 + vector hybrid retrieval
              </p>
            </div>
            {currentDoc && (
              <div className="grid grid-cols-1 gap-2">
                {SUGGESTIONS.map(s => (
                  <button key={s}
                    onClick={() => sendQuery(s)}
                    className="text-left px-3 py-2.5 rounded-xl text-xs border transition-all"
                    style={{
                      background:   'var(--bg-card)',
                      borderColor:  'var(--border)',
                      color:        'var(--text-secondary)',
                    }}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`animate-fade-in ${msg.role === 'user' ? 'flex justify-end' : ''}`}>

              {/* ── User bubble ── */}
              {msg.role === 'user' ? (
                <div className="max-w-[85%] px-3.5 py-2.5 text-sm"
                     style={{
                       background:   '#1e3a1e',
                       border:       '1px solid rgba(198,241,53,0.25)',
                       borderRadius: '16px 16px 4px 16px',
                       color:        'var(--text-primary)',
                       lineHeight:   '1.55',
                     }}>
                  {msg.content}
                </div>
              ) : (

                /* ── Assistant bubble ── */
                <div className="group">
                  {/* Confidence badge — own row, ABOVE the answer */}
                  {!msg.streaming && msg.confidence && (
                    <div className="mb-2">
                      <ConfidenceBadge confidence={msg.confidence} />
                    </div>
                  )}

                  {/* Answer bubble */}
                  <div className="px-3.5 py-3"
                       style={{
                         background:   msg.isError ? 'rgba(248,113,113,0.06)' : '#1a1a1a',
                         borderLeft:   `3px solid ${msg.isError ? 'var(--red)' : 'var(--volt)'}`,
                         border:       `1px solid ${msg.isError ? 'var(--red-border)' : 'var(--border-card)'}`,
                         borderRadius: '4px 12px 12px 12px',
                       }}>
                    {msg.streaming ? (
                      <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                        {msg.content ? (
                          <>
                            {msg.content}
                            <span className="inline-block w-0.5 h-4 ml-0.5 align-text-bottom animate-cursor-blink"
                                  style={{ background: 'var(--volt)' }} />
                          </>
                        ) : (
                          <span className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                            <span className="flex gap-1">
                              {[0, 150, 300].map(d => (
                                <span key={d}
                                  className="w-1.5 h-1.5 rounded-full inline-block"
                                  style={{
                                    background:      'var(--volt)',
                                    animation:       'bounce-dot 1.2s ease-in-out infinite',
                                    animationDelay:  `${d}ms`,
                                  }} />
                              ))}
                            </span>
                            Retrieving…
                          </span>
                        )}
                      </div>
                    ) : (
                      <MarkdownMessage content={msg.content} />
                    )}
                  </div>

                  {/* Actions row (visible on hover) */}
                  {!msg.streaming && (
                    <div className="flex items-center gap-1.5 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => copyMessage(msg.id, msg.content)}
                        className="flex items-center gap-1 text-xs px-2 py-0.5 rounded font-mono-ui"
                        style={{ color: 'var(--text-muted)', background: 'var(--bg-card)' }}>
                        {copiedMsg === msg.id
                          ? <><Check className="w-3 h-3" /> Copied</>
                          : <><Copy  className="w-3 h-3" /> Copy</>}
                      </button>
                      {msg.id === messages[messages.length - 1]?.id && (
                        <button onClick={handleRetry}
                          className="flex items-center gap-1 text-xs px-2 py-0.5 rounded font-mono-ui"
                          style={{ color: 'var(--text-muted)', background: 'var(--bg-card)' }}>
                          <RotateCcw className="w-3 h-3" /> Retry
                        </button>
                      )}
                      {/* Feedback thumbs — only if we have a query_id and no feedback yet */}
                      {msg.query_id && (
                        <>
                          <button
                            onClick={() => msg.feedback === null && submitFeedback(msg.id, msg.query_id, 1)}
                            disabled={msg.feedback !== null && msg.feedback !== undefined}
                            title="Helpful"
                            className="p-1 rounded"
                            style={{
                              color: msg.feedback === 1 ? 'var(--volt)' : 'var(--text-muted)',
                              background: msg.feedback === 1 ? 'var(--volt-dim)' : 'var(--bg-card)',
                              cursor: msg.feedback !== null && msg.feedback !== undefined ? 'default' : 'pointer',
                            }}>
                            <ThumbsUp className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => msg.feedback === null && submitFeedback(msg.id, msg.query_id, -1)}
                            disabled={msg.feedback !== null && msg.feedback !== undefined}
                            title="Not helpful"
                            className="p-1 rounded"
                            style={{
                              color: msg.feedback === -1 ? 'var(--red)' : 'var(--text-muted)',
                              background: msg.feedback === -1 ? 'var(--red-dim)' : 'var(--bg-card)',
                              cursor: msg.feedback !== null && msg.feedback !== undefined ? 'default' : 'pointer',
                            }}>
                            <ThumbsDown className="w-3 h-3" />
                          </button>
                        </>
                      )}
                    </div>
                  )}

                  {/* Sources */}
                  {!msg.streaming && msg.sources?.length > 0 && (
                    <div className="mt-2.5 space-y-1.5">
                      <div className="source-pill" style={{ cursor: 'default' }}>
                        <span aria-hidden="true">◈</span>
                        {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
                      </div>
                      {msg.sources.slice(0, 3).map((src, si) => (
                        <SourceCard key={si} src={src} onJumpToPdf={onJumpToPdf} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ─── Input area ──────────────────────────────────────────────────── */}
      <div className="px-3 pb-3 pt-2 border-t flex-shrink-0"
           style={{ borderColor: 'var(--border)' }}>
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!currentDoc || streaming}
            placeholder={currentDoc ? 'Ask anything… (Enter to send)' : 'Select a document first'}
            rows={2}
            className="flex-1 rounded-xl px-3 py-2.5 text-sm resize-none border outline-none transition-colors"
            style={{
              background:   'var(--bg-card)',
              borderColor:  'var(--border-card)',
              color:        'var(--text-primary)',
            }}
          />
          <div className="flex items-center gap-1.5">
            <button
              title="Query guard: injection & length protection active"
              className="p-1.5 rounded-lg cursor-default"
              style={{ color: 'var(--text-muted)', background: 'transparent' }}
              tabIndex={-1}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--volt)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
            >
              <Shield className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => sendQuery()}
              disabled={!currentDoc || !query.trim() || streaming}
              className="p-2.5 rounded-xl flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              style={{ background: 'var(--volt)', color: '#000' }}>
              {streaming
                ? <span className="w-4 h-4 border-2 rounded-full animate-spin block"
                        style={{ borderColor: 'rgba(0,0,0,0.3)', borderTopColor: '#000' }} />
                : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <p className="text-xs mt-1.5 px-1 font-mono-ui" style={{ color: 'var(--text-faint)' }}>
          Shift+Enter for newline · Enter to send
        </p>
      </div>
    </div>
  );
}
