import React, { useState, useEffect } from 'react';
import { FileText, Code, Loader, AlertCircle, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

function getExtension(filename) {
  if (!filename) return '';
  return filename.substring(filename.lastIndexOf('.')).toLowerCase();
}

function getLanguage(filename) {
  const ext = getExtension(filename);
  const map = {
    '.md': 'markdown', '.txt': 'text', '.html': 'html', '.htm': 'html',
    '.js': 'javascript', '.jsx': 'javascript', '.ts': 'typescript', '.tsx': 'typescript',
    '.py': 'python', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
    '.css': 'css', '.scss': 'scss', '.xml': 'xml', '.sh': 'bash',
    '.go': 'go', '.rs': 'rust', '.java': 'java', '.rb': 'ruby',
  };
  return map[ext] || 'text';
}

function getBadge(filename) {
  const ext = getExtension(filename);
  const map = {
    '.md':   { label: 'Markdown', cls: 'bg-blue-500/20 text-blue-300' },
    '.html': { label: 'HTML',     cls: 'bg-orange-500/20 text-orange-300' },
    '.htm':  { label: 'HTML',     cls: 'bg-orange-500/20 text-orange-300' },
    '.txt':  { label: 'Text',     cls: 'bg-slate-500/20 text-slate-300' },
    '.py':   { label: 'Python',   cls: 'bg-yellow-500/20 text-yellow-300' },
    '.js':   { label: 'JS',       cls: 'bg-yellow-500/20 text-yellow-300' },
    '.ts':   { label: 'TS',       cls: 'bg-blue-500/20 text-blue-300' },
    '.json': { label: 'JSON',     cls: 'bg-green-500/20 text-green-300' },
  };
  return map[ext] || { label: ext.replace('.', '').toUpperCase() || 'FILE', cls: 'bg-slate-500/20 text-slate-300' };
}

export default function TextViewer({ fileUrl, filename, fileContent, darkMode }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (fileContent) {
      setContent(fileContent);
      setLoading(false);
    } else if (fileUrl) {
      fetch(fileUrl)
        .then(r => { if (!r.ok) throw new Error('Failed to load'); return r.text(); })
        .then(t => { setContent(t); setLoading(false); })
        .catch(e => { setError(e.message); setLoading(false); });
    } else {
      setLoading(false);
      setError('No file provided');
    }
  }, [fileUrl, fileContent]);

  const copyContent = () => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-base)' }}>
      <div className="text-center">
        <Loader className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: 'var(--accent)' }} />
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-base)' }}>
      <div className="text-center max-w-md px-4">
        <AlertCircle className="w-10 h-10 mx-auto mb-3" style={{ color: '#f87171' }} />
        <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Error loading document</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{error}</p>
      </div>
    </div>
  );

  if (!content) return (
    <div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-base)' }}>
      <div className="text-center">
        <FileText className="w-10 h-10 mx-auto mb-3 opacity-20" />
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No content</p>
      </div>
    </div>
  );

  const ext = getExtension(filename);
  const isMarkdown = ext === '.md';
  const isHTML = ext === '.html' || ext === '.htm';
  const badge = getBadge(filename);
  const lang = getLanguage(filename);

  // Safely strip HTML to plain text (avoids XSS)
  const safeHTMLText = (html) => {
    try {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      return doc.body.innerText || doc.body.textContent || html;
    } catch { return html; }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Header bar */}
      <div className="px-5 py-3 border-b flex items-center justify-between flex-shrink-0"
           style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 min-w-0">
          <FileText className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent)' }} />
          <div className="min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>{filename}</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {content.length.toLocaleString()} chars · {content.split('\n').length.toLocaleString()} lines
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>{badge.label}</span>
          <button onClick={copyContent}
            className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-secondary)' }}>
            {copied ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-5 min-h-0">
        <div className="max-w-4xl mx-auto">
          {isMarkdown ? (
            <div className="prose-dark px-1">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    if (inline) {
                      return (
                        <code style={{ background: 'var(--bg-surface-2)', color: '#e879f9', border: '1px solid var(--border)', borderRadius: '3px', padding: '0.1em 0.35em', fontSize: '0.85em' }} {...props}>
                          {children}
                        </code>
                      );
                    }
                    const lang = className?.replace('language-', '') || '';
                    return (
                      <div style={{ background: '#0f172a', borderRadius: '0.5rem', border: '1px solid var(--border)', overflow: 'hidden', margin: '0.75em 0' }}>
                        <div style={{ borderBottom: '1px solid var(--border)', padding: '0.375rem 0.75rem', fontSize: '11px', color: 'var(--text-muted)' }}>{lang || 'code'}</div>
                        <pre style={{ margin: 0, padding: '1rem', background: 'transparent', overflow: 'auto' }}>
                          <code className={className}>{children}</code>
                        </pre>
                      </div>
                    );
                  },
                  pre({ children }) { return <>{children}</>; },
                }}>
                {content}
              </ReactMarkdown>
            </div>
          ) : isHTML ? (
            <div className="rounded-xl p-6 border prose-dark"
                 style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
              <p className="text-xs mb-3 pb-3 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
                HTML rendered as plain text (safe mode)
              </p>
              <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans"
                   style={{ color: 'var(--text-primary)' }}>
                {safeHTMLText(content)}
              </pre>
            </div>
          ) : (
            <div className="rounded-xl overflow-hidden border"
                 style={{ background: '#0f172a', borderColor: 'var(--border)' }}>
              <div className="px-4 py-2 flex items-center justify-between border-b"
                   style={{ borderColor: 'var(--border)' }}>
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{lang}</span>
                <Code className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
              </div>
              <pre className="p-5 overflow-x-auto text-sm leading-relaxed" style={{ margin: 0 }}>
                <code className={`language-${lang} hljs`}
                      dangerouslySetInnerHTML={{
                        __html: (() => {
                          try {
                            const hljs = require('highlight.js/lib/core');
                            const hlMap = { javascript: 'javascript', python: 'python', json: 'json', yaml: 'yaml', css: 'css', bash: 'bash', text: null };
                            if (!hlMap[lang]) return content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                            return hljs.highlight(content, { language: lang }).value;
                          } catch { return content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
                        })()
                      }} />
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
