import React, { useState, useEffect } from 'react';
import { FileText, Code, Loader, AlertCircle } from 'lucide-react';

export default function TextViewer({ fileUrl, filename, fileContent }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (fileContent) {
      // Content provided directly
      setContent(fileContent);
      setLoading(false);
    } else if (fileUrl) {
      // Fetch content from URL
      fetch(fileUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to load file');
          }
          return response.text();
        })
        .then(text => {
          setContent(text);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    } else {
      setLoading(false);
      setError('No file provided');
    }
  }, [fileUrl, fileContent]);

  const getFileExtension = () => {
    if (!filename) return '';
    const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
    return ext;
  };

  const getLanguage = () => {
    const ext = getFileExtension();
    const langMap = {
      '.md': 'markdown',
      '.txt': 'text',
      '.html': 'html',
      '.htm': 'html',
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.json': 'json',
      '.yaml': 'yaml',
      '.yml': 'yaml',
      '.css': 'css',
      '.scss': 'scss',
      '.xml': 'xml',
    };
    return langMap[ext] || 'text';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center max-w-md px-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-600 font-medium mb-2">Error loading document</p>
          <p className="text-sm text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No content to display</p>
        </div>
      </div>
    );
  }

  const isMarkdown = getFileExtension() === '.md';
  const isHTML = getFileExtension() === '.html' || getFileExtension() === '.htm';
  const language = getLanguage();

  return (
    <div className="flex flex-col h-full bg-gray-50 overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-gray-600" />
          <div>
            <h3 className="text-sm font-semibold text-gray-900 truncate max-w-md">
              {filename}
            </h3>
            <p className="text-xs text-gray-500">
              {content.length.toLocaleString()} characters · {content.split('\n').length} lines
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isMarkdown && (
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
              Markdown
            </span>
          )}
          {isHTML && (
            <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-700 rounded">
              HTML
            </span>
          )}
          {getFileExtension() === '.txt' && (
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
              Text
            </span>
          )}
        </div>
      </div>

      {/* Content - Independent scroll area */}
      <div className="flex-1 overflow-auto p-6 min-h-0">
        <div className="max-w-4xl mx-auto">
          {isHTML ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div 
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: content }}
              />
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <pre className="p-6 overflow-x-auto text-sm font-mono leading-relaxed">
                <code className={`language-${language}`}>{content}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

