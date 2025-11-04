import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, MessageSquare, Code, FileText, X, GripVertical } from 'lucide-react';
import { API_BASE } from '../config';

export default function QuerySidebar({ currentDoc, onQuery, isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [querying, setQuerying] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(384); // Default 384px (w-96)
  const chatEndRef = useRef(null);
  const sidebarRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle resizing
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      // Clamp width between 300px and 800px
      const clampedWidth = Math.max(300, Math.min(800, newWidth));
      setSidebarWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // Extract and render code blocks from text
  const renderMessageContent = (content) => {
    if (!content) return '';

    // Split content by code blocks (```language\ncode\n```)
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        const textContent = content.substring(lastIndex, match.index);
        if (textContent.trim()) {
          parts.push({ type: 'text', content: textContent });
        }
      }

      // Add code block
      parts.push({
        type: 'code',
        language: match[1] || 'text',
        content: match[2],
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      const textContent = content.substring(lastIndex);
      if (textContent.trim()) {
        parts.push({ type: 'text', content: textContent });
      }
    }

    // If no code blocks found, return original content as text
    if (parts.length === 0) {
      parts.push({ type: 'text', content });
    }

    return parts;
  };

  const handleQuery = async () => {
    if (!query.trim() || querying || !currentDoc) return;

    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setQuerying(true);

    try {
      const response = await fetch(`${API_BASE}/chat/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage.content,
          doc_id: currentDoc?.doc_id,
          top_k: 5,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Query failed');
      }

      const result = await response.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`,
        isError: true,
      }]);
    } finally {
      setQuerying(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      ref={sidebarRef}
      className="bg-white border-l border-gray-200 flex flex-col shadow-xl h-full relative"
      style={{ width: `${sidebarWidth}px`, minWidth: '300px', maxWidth: '800px' }}
    >
      {/* Resize handle */}
      <div
        onMouseDown={(e) => {
          e.preventDefault();
          setIsResizing(true);
        }}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 transition-colors z-10"
        style={{ cursor: 'col-resize' }}
      >
        <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <GripVertical className="w-4 h-4 text-gray-400" />
        </div>
      </div>

      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900">Query Assistant</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <X className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* Messages - Independent scroll area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-sm">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Ask about your document
              </h4>
              <p className="text-xs text-gray-500">
                Type your question below to get AI-powered answers based on your uploaded document.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => {
              const contentParts = renderMessageContent(msg.content);
              
              return (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] ${msg.role === 'user' ? 'w-auto' : 'w-full'}`}>
                    <div className={`
                      rounded-lg px-3 py-2 text-sm
                      ${msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : msg.isError
                          ? 'bg-red-50 text-red-900 border border-red-200'
                          : 'bg-gray-50 text-gray-900 border border-gray-200'
                      }
                    `}>
                      {/* Render content parts */}
                      <div className="space-y-2">
                        {contentParts.map((part, partIdx) => {
                          if (part.type === 'code') {
                            return (
                              <div key={partIdx} className="mt-2">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-mono text-gray-500">
                                    {part.language}
                                  </span>
                                  <button
                                    onClick={() => {
                                      navigator.clipboard.writeText(part.content);
                                    }}
                                    className="text-xs text-gray-500 hover:text-gray-700"
                                    title="Copy code"
                                  >
                                    Copy
                                  </button>
                                </div>
                                <pre className={`
                                  p-3 rounded bg-gray-900 text-gray-100 
                                  overflow-x-auto text-xs font-mono
                                  whitespace-pre-wrap break-words
                                  ${msg.role === 'user' ? 'bg-gray-800' : ''}
                                `}>
                                  <code className={`language-${part.language}`}>
                                    {part.content}
                                  </code>
                                </pre>
                              </div>
                            );
                          } else {
                            return (
                              <div 
                                key={partIdx} 
                                className="whitespace-pre-wrap break-words leading-relaxed"
                                style={{ wordWrap: 'break-word', overflowWrap: 'break-word' }}
                              >
                                {part.content}
                              </div>
                            );
                          }
                        })}
                      </div>
                    </div>
                    
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {msg.sources.slice(0, 2).map((source, sidx) => (
                          <div key={sidx} className="bg-white rounded border border-gray-200 p-2 text-xs">
                            <div className="flex items-center gap-1 mb-1">
                              {source.metadata.type === 'code' ? (
                                <Code className="w-3 h-3 text-blue-600" />
                              ) : (
                                <FileText className="w-3 h-3 text-gray-600" />
                              )}
                              <span className="font-medium text-gray-700 truncate">
                                {source.metadata.heading || 'No heading'}
                              </span>
                              <span className="text-gray-400 ml-auto flex-shrink-0">
                                {(source.relevance_score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="text-gray-600 line-clamp-2 break-words">
                              {source.content.substring(0, 100)}...
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {querying && (
              <div className="flex justify-start">
                <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 flex items-center gap-2">
                  <Loader className="w-3 h-3 animate-spin text-blue-600" />
                  <span className="text-xs text-gray-600">Thinking...</span>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </>
        )}
      </div>

      {/* Input - Fixed at bottom */}
      <div className="border-t border-gray-200 bg-white p-4 flex-shrink-0">
        <div className="flex gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={currentDoc ? "Ask about the document..." : "Select a document first..."}
            disabled={!currentDoc || querying}
            rows={3}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed resize-none break-words"
            style={{ wordWrap: 'break-word', overflowWrap: 'break-word' }}
          />
          <button
            onClick={handleQuery}
            disabled={!currentDoc || !query.trim() || querying}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-1 self-end"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
