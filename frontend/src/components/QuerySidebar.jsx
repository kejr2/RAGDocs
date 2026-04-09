import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, X, Code, FileText, Copy, Check, RotateCcw,
  Trash2, Clock, Zap, MessageSquare
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { API_BASE } from '../config';

const HISTORY_KEY = 'ragdocs_query_history';
const MAX_HISTORY = 20;

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
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, MAX_HISTORY))); } catch {}
}

function CodeBlock({ children, className }) {
  const [copied, setCopied] = useState(false);
  const code = String(children).replace(/\n$/, '');
  const lang = className?.replace('language-', '') || '';

  const copy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="relative my-2 rounded-xl overflow-hidden border"
         style={{ borderColor: 'var(--border)', background: '#0f172a' }}>
      <div className="flex items-center justify-between px-3 py-1.5"
           style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{lang || 'code'}</span>
        <button onClick={copy}
          className="flex items-center gap-1 text-xs px-2 py-0.5 rounded"
          style={{ color: copied ? '#4ade80' : 'var(--text-muted)', background: 'var(--bg-surface-2)' }}>
          {copied ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
        </button>
      </div>
      <pre style={{ margin: 0, background: 'transparent', padding: '1rem' }}>
        <code className={className}>{code}</code>
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
          code({ node, inline, className, children, ...props }) {
            if (inline) {
              return (
                <code className="px-1 py-0.5 rounded text-xs"
                      style={{ background: 'var(--bg-surface-2)', color: '#e879f9', border: '1px solid var(--border)' }}
                      {...props}>
                  {children}
                </code>
              );
            }
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

export default function QuerySidebar({ currentDoc, isOpen, onClose, darkMode }) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('ragdocs_messages') || '[]'); } catch { return []; }
  });
  const [streaming, setStreaming] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const [history, setHistory] = useState(loadHistory);
  const [showHistory, setShowHistory] = useState(false);
  const [copiedMsg, setCopiedMsg] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Persist messages to sessionStorage (survives page refresh within same tab)
  useEffect(() => {
    try { sessionStorage.setItem('ragdocs_messages', JSON.stringify(messages)); } catch {}
  }, [messages]);

  const addToHistory = useCallback((q) => {
    setHistory(prev => {
      const next = [q, ...prev.filter(h => h !== q)].slice(0, MAX_HISTORY);
      saveHistory(next);
      return next;
    });
  }, []);

  const sendQuery = useCallback(async (queryText) => {
    const q = (queryText || query).trim();
    if (!q || streaming) return;

    setQuery('');
    setShowHistory(false);
    addToHistory(q);

    const userMsg = { id: crypto.randomUUID(), role: 'user', content: q };
    const assistantMsg = { id: crypto.randomUUID(), role: 'assistant', content: '', streaming: true, sources: [] };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    // Abort any previous in-flight request, then set new controller
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, doc_id: currentDoc?.doc_id || null, top_k: 8 }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

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
                  next[next.length - 1] = { ...last, streaming: false, sources: data.sources || [] };
                }
                return next;
              });
            } else if (data.error) {
              throw new Error(data.error);
            }
          } catch (_) { /* skip malformed SSE lines */ }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        processLines();
      }
      // Flush remaining bytes in the decoder after stream ends
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
      // Fallback to non-streaming endpoint
      try {
        const res = await fetch(`${API_BASE}/chat/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, doc_id: currentDoc?.doc_id || null, top_k: 8 }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Query failed');
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1] = {
            role: 'assistant', content: data.answer,
            streaming: false, sources: data.sources || []
          };
          return next;
        });
      } catch (fallbackErr) {
        setMessages(prev => {
          const next = [...prev];
          next[next.length - 1] = {
            role: 'assistant', content: `Error: ${fallbackErr.message}`,
            streaming: false, isError: true, sources: []
          };
          return next;
        });
      }
    } finally {
      clearTimeout(timeoutId);
      setStreaming(false);
    }
  }, [query, streaming, currentDoc, addToHistory]);

  const handleKeyDown = (e) => {
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

  // Drag resize
  const startResize = (e) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startW = sidebarWidth;
    const onMove = (me) => setSidebarWidth(Math.max(320, Math.min(800, startW + startX - me.clientX)));
    const onUp = () => { setIsResizing(false); document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="relative flex flex-col h-full flex-shrink-0 border-l"
         style={{ width: sidebarWidth, background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>

      {/* Resize handle */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10 transition-colors"
        style={{ background: isResizing ? 'var(--accent)' : 'transparent' }}
        onMouseDown={startResize}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; }}
        onMouseLeave={e => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }}
      />

      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0"
           style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" style={{ color: 'var(--accent)' }} />
          <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>AI Assistant</span>
          {currentDoc && (
            <span className="text-xs px-2 py-0.5 rounded-full max-w-[120px] truncate"
                  style={{ background: 'var(--accent-light)', color: 'var(--accent)' }}>
              {currentDoc.filename}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {hasMessages && (
            <button onClick={() => setMessages([])}
              className="p-1.5 rounded-lg" title="Clear conversation"
              style={{ color: 'var(--text-muted)', background: 'var(--bg-surface-2)' }}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button onClick={onClose} className="p-1.5 rounded-lg"
            style={{ color: 'var(--text-muted)', background: 'var(--bg-surface-2)' }}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
        {!hasMessages ? (
          <div className="space-y-4 animate-fade-in">
            <div className="text-center py-6">
              <Zap className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                {currentDoc ? 'Ask anything about this document' : 'Upload a document to start'}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                Responses stream in real time
              </p>
            </div>
            {currentDoc && (
              <div className="grid grid-cols-2 gap-2">
                {SUGGESTIONS.map(s => (
                  <button key={s}
                    onClick={() => sendQuery(s)}
                    className="text-left px-3 py-2.5 rounded-xl text-xs border transition-all hover:opacity-80"
                    style={{ background: 'var(--bg-surface-2)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`animate-fade-in ${msg.role === 'user' ? 'flex justify-end' : ''}`}>
              {msg.role === 'user' ? (
                <div className="max-w-[85%] px-3 py-2 rounded-2xl rounded-tr-sm text-sm"
                     style={{ background: 'var(--accent)', color: '#fff' }}>
                  {msg.content}
                </div>
              ) : (
                <div className="group">
                  <div className="rounded-2xl rounded-tl-sm px-3 py-2.5 border"
                       style={{
                         background: msg.isError ? 'rgba(239,68,68,0.08)' : 'var(--bg-surface-2)',
                         borderColor: msg.isError ? 'rgba(239,68,68,0.25)' : 'var(--border)',
                       }}>
                    {msg.streaming ? (
                      <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                        {msg.content ? (
                          <>
                            {msg.content}
                            <span className="inline-block w-0.5 h-4 ml-0.5 align-text-bottom animate-cursor-blink"
                                  style={{ background: 'var(--accent)' }} />
                          </>
                        ) : (
                          <span className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                            <span className="flex gap-1">
                              {[0, 150, 300].map(d => (
                                <span key={d} className="w-1.5 h-1.5 rounded-full animate-bounce inline-block"
                                      style={{ background: 'var(--accent)', animationDelay: `${d}ms` }} />
                              ))}
                            </span>
                            Thinking…
                          </span>
                        )}
                      </div>
                    ) : (
                      <MarkdownMessage content={msg.content} />
                    )}
                  </div>

                  {/* Message actions */}
                  {!msg.streaming && (
                    <div className="flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => copyMessage(msg.id, msg.content)}
                        className="flex items-center gap-1 text-xs px-2 py-0.5 rounded"
                        style={{ color: 'var(--text-muted)', background: 'var(--bg-surface-2)' }}>
                        {copiedMsg === msg.id
                          ? <><Check className="w-3 h-3" /> Copied</>
                          : <><Copy className="w-3 h-3" /> Copy</>}
                      </button>
                      {msg.id === messages[messages.length - 1]?.id && (
                        <button onClick={handleRetry}
                          className="flex items-center gap-1 text-xs px-2 py-0.5 rounded"
                          style={{ color: 'var(--text-muted)', background: 'var(--bg-surface-2)' }}>
                          <RotateCcw className="w-3 h-3" /> Retry
                        </button>
                      )}
                    </div>
                  )}

                  {/* Sources */}
                  {!msg.streaming && msg.sources?.length > 0 && (
                    <div className="mt-2 space-y-1.5">
                      <p className="text-xs font-medium px-1" style={{ color: 'var(--text-muted)' }}>
                        {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
                      </p>
                      {msg.sources.slice(0, 3).map((src, si) => (
                        <div key={si} className="rounded-xl p-2.5 border text-xs"
                             style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
                          <div className="flex items-center gap-2 mb-1">
                            {src.metadata?.type === 'code'
                              ? <Code className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                              : <FileText className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />}
                            <span className="font-medium truncate flex-1" style={{ color: 'var(--text-secondary)' }}>
                              {src.metadata?.heading || src.metadata?.source_file || 'Source'}
                            </span>
                            <span className="flex-shrink-0 px-1.5 py-0.5 rounded-full font-medium"
                                  style={{ background: 'var(--accent-light)', color: 'var(--accent)' }}>
                              {Math.round((src.relevance_score || 0) * 100)}%
                            </span>
                          </div>
                          <p style={{ color: 'var(--text-muted)', lineHeight: '1.5' }}>
                            {src.content?.slice(0, 200)}{src.content?.length > 200 ? '…' : ''}
                          </p>
                        </div>
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

      {/* Input area */}
      <div className="px-3 pb-3 pt-2 border-t flex-shrink-0"
           style={{ borderColor: 'var(--border)' }}>

        {/* History dropdown */}
        {showHistory && history.length > 0 && (
          <div className="mb-2 rounded-xl border overflow-hidden shadow-lg animate-fade-in"
               style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
            <p className="text-xs font-medium px-3 py-1.5 border-b"
               style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
              Recent queries
            </p>
            <div className="max-h-40 overflow-y-auto">
              {history.slice(0, 8).map((h, i) => (
                <button key={h}
                  onClick={() => { setQuery(h); setShowHistory(false); textareaRef.current?.focus(); }}
                  className="w-full text-left px-3 py-1.5 text-xs truncate hover:opacity-80"
                  style={{
                    color: 'var(--text-secondary)',
                    borderBottom: i < Math.min(7, history.length - 1) ? '1px solid var(--border)' : 'none'
                  }}>
                  {h}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            {history.length > 0 && (
              <button
                onClick={() => setShowHistory(s => !s)}
                className="absolute right-2 top-2 p-0.5 rounded"
                style={{ color: showHistory ? 'var(--accent)' : 'var(--text-muted)' }}
                title="Query history">
                <Clock className="w-3.5 h-3.5" />
              </button>
            )}
            <textarea
              ref={textareaRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!currentDoc || streaming}
              placeholder={currentDoc ? 'Ask anything… (Enter to send)' : 'Select a document first'}
              rows={2}
              className="w-full rounded-xl px-3 py-2.5 pr-8 text-sm resize-none border outline-none"
              style={{
                background: 'var(--bg-surface-2)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
          <button
            onClick={() => sendQuery()}
            disabled={!currentDoc || !query.trim() || streaming}
            className="p-2.5 rounded-xl flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: 'var(--accent)', color: '#fff' }}>
            {streaming
              ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin block" />
              : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-xs mt-1 px-1" style={{ color: 'var(--text-muted)' }}>
          Shift+Enter for newline · Enter to send
        </p>
      </div>
    </div>
  );
}
