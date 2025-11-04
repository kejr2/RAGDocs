import React, { useState, useRef } from 'react';
import { Upload, FileText, Code, Trash2, Loader, CheckCircle, XCircle, Book, MessageSquare, X, FileUp } from 'lucide-react';
import PDFViewer from './components/PDFViewer';
import TextViewer from './components/TextViewer';
import QuerySidebar from './components/QuerySidebar';
import { API_BASE } from './config';

const SUPPORTED_TYPES = [
  { ext: '.pdf', name: 'PDF', icon: '📄', color: 'text-red-600' },
  { ext: '.md', name: 'Markdown', icon: '📝', color: 'text-blue-600' },
  { ext: '.txt', name: 'Text', icon: '📋', color: 'text-gray-600' },
  { ext: '.html', name: 'HTML', icon: '🌐', color: 'text-orange-600' },
  { ext: '.htm', name: 'HTML', icon: '🌐', color: 'text-orange-600' },
];

const ACCEPT_TYPES = '.pdf,.md,.txt,.html,.htm';

export default function RAGDocsApp() {
  const [documents, setDocuments] = useState([]);
  const [currentDoc, setCurrentDoc] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [showQuerySidebar, setShowQuerySidebar] = useState(true);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [textContent, setTextContent] = useState(null);
  const [textFilename, setTextFilename] = useState(null);
  const fileInputRef = useRef(null);

  // Get document types currently uploaded
  const getUploadedTypes = () => {
    const types = new Set();
    documents.forEach(doc => {
      const ext = doc.filename.substring(doc.filename.lastIndexOf('.')).toLowerCase();
      types.add(ext);
    });
    return Array.from(types);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadStatus(null);

    // Prepare file for viewing
    if (file.type === 'application/pdf') {
      // PDF - create blob URL
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
      setTextContent(null);
      setTextFilename(null);
    } else {
      // Text files - read content immediately
      setPdfUrl(null);
      const reader = new FileReader();
      reader.onload = (e) => {
        setTextContent(e.target.result);
        setTextFilename(file.name);
      };
      reader.readAsText(file);
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/docs/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();
      setDocuments([...documents, result]);
      setCurrentDoc(result);
      setUploadStatus({ type: 'success', message: `Uploaded ${result.total_chunks} chunks!` });
    } catch (error) {
      setUploadStatus({ type: 'error', message: error.message });
      // Clear content on error
      setPdfUrl(null);
      setTextContent(null);
      setTextFilename(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!confirm('Delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE}/docs/documents/${docId}`, { 
        method: 'DELETE' 
      });
      
      if (!response.ok) {
        throw new Error('Delete failed');
      }

      setDocuments(documents.filter(d => d.doc_id !== docId));
      if (currentDoc?.doc_id === docId) {
        setCurrentDoc(null);
        setPdfUrl(null);
        setTextContent(null);
        setTextFilename(null);
      }
    } catch (error) {
      alert('Failed to delete document');
    }
  };

  const handleDocSelect = async (doc) => {
    setCurrentDoc(doc);
    
    // Check if we need to reload content
    // For PDFs, we need to check if pdfUrl matches
    // For text files, we need to check if textContent matches
    
    const ext = doc.filename.substring(doc.filename.lastIndexOf('.')).toLowerCase();
    if (ext === '.pdf') {
      // PDF - we'd need to fetch from server or store URL
      // For now, if pdfUrl is not set, we can't show it
      // In production, you'd fetch the PDF from the backend
    } else {
      // Text file - we'd need to fetch from server
      // For now, if textContent is not set, we can't show it
      // In production, you'd fetch the content from the backend
    }
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex overflow-hidden">
      {/* Left Sidebar - Documents */}
      <div className="w-72 bg-white border-r border-gray-200 flex flex-col shadow-lg h-full overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-gray-200 bg-gradient-to-br from-blue-600 to-indigo-600 flex-shrink-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
              <Book className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">RAG Docs</h1>
              <p className="text-xs text-blue-100">AI Documentation Assistant</p>
            </div>
          </div>

          {/* Upload Button */}
          <label className="block">
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              accept={ACCEPT_TYPES}
              className="hidden"
              disabled={uploading}
            />
            <div className={`
              flex items-center justify-center gap-2 px-4 py-3 rounded-lg cursor-pointer
              transition-all duration-200 shadow-md
              ${uploading 
                ? 'bg-white/20 cursor-not-allowed' 
                : 'bg-white hover:bg-blue-50 text-blue-600 hover:shadow-lg'
              }
            `}>
              {uploading ? (
                <><Loader className="w-4 h-4 animate-spin" /> Uploading...</>
              ) : (
                <><FileUp className="w-4 h-4" /> Upload Document</>
              )}
            </div>
          </label>

          {/* Supported Document Types */}
          <div className="mt-4 p-3 bg-white/10 rounded-lg backdrop-blur-sm">
            <p className="text-xs font-semibold text-blue-100 mb-2 uppercase tracking-wide">
              Supported Types
            </p>
            <div className="flex flex-wrap gap-2">
              {SUPPORTED_TYPES.map((type, idx) => {
                const isUploaded = getUploadedTypes().includes(type.ext.toLowerCase());
                return (
                  <div
                    key={idx}
                    className={`
                      px-2 py-1 rounded text-xs flex items-center gap-1
                      ${isUploaded 
                        ? 'bg-green-500/30 text-green-100 border border-green-400/50' 
                        : 'bg-white/20 text-blue-100 border border-white/30'
                      }
                    `}
                    title={isUploaded ? 'Currently uploaded' : 'Supported'}
                  >
                    <span>{type.icon}</span>
                    <span>{type.name}</span>
                    {isUploaded && <span className="ml-1">✓</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {uploadStatus && (
            <div className={`mt-3 p-3 rounded-lg text-sm flex items-center gap-2 ${
              uploadStatus.type === 'success' ? 'bg-green-500/20 text-green-100 border border-green-400/30' : 'bg-red-500/20 text-red-100 border border-red-400/30'
            }`}>
              {uploadStatus.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              {uploadStatus.message}
            </div>
          )}
        </div>

        {/* Documents List - Independent scroll area */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3 px-2">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Documents ({documents.length})
              </h2>
              {documents.length > 0 && (
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <span className="font-medium">Types:</span>
                  <div className="flex gap-1">
                    {getUploadedTypes().map((ext, idx) => {
                      const type = SUPPORTED_TYPES.find(t => t.ext.toLowerCase() === ext);
                      return type ? (
                        <span key={idx} className={type.color} title={type.name}>
                          {type.icon}
                        </span>
                      ) : null;
                    })}
                  </div>
                </div>
              )}
            </div>
            {documents.length === 0 ? (
              <div className="text-center py-12 px-4">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-400">
                  No documents yet.<br/>Upload one to start!
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className={`
                      group p-3 rounded-xl cursor-pointer transition-all duration-200
                      ${currentDoc?.doc_id === doc.doc_id 
                        ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 shadow-md' 
                        : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent hover:border-gray-200'
                      }
                    `}
                    onClick={() => handleDocSelect(doc)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          {(() => {
                            const ext = doc.filename.substring(doc.filename.lastIndexOf('.')).toLowerCase();
                            const type = SUPPORTED_TYPES.find(t => t.ext.toLowerCase() === ext);
                            return type ? (
                              <span className={`text-lg flex-shrink-0 ${currentDoc?.doc_id === doc.doc_id ? 'text-blue-600' : 'text-gray-400'}`}>
                                {type.icon}
                              </span>
                            ) : (
                              <FileText className={`w-4 h-4 flex-shrink-0 ${currentDoc?.doc_id === doc.doc_id ? 'text-blue-600' : 'text-gray-400'}`} />
                            );
                          })()}
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium truncate ${currentDoc?.doc_id === doc.doc_id ? 'text-blue-900' : 'text-gray-900'}`}>
                              {doc.filename}
                            </p>
                            {(() => {
                              const ext = doc.filename.substring(doc.filename.lastIndexOf('.')).toLowerCase();
                              const type = SUPPORTED_TYPES.find(t => t.ext.toLowerCase() === ext);
                              return type ? (
                                <span className={`text-xs ${currentDoc?.doc_id === doc.doc_id ? 'text-blue-600' : 'text-gray-500'}`}>
                                  {type.name}
                                </span>
                              ) : null;
                            })()}
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500 ml-6">
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3" /> {doc.text_chunks}
                          </span>
                          <span className="flex items-center gap-1">
                            <Code className="w-3 h-3" /> {doc.code_chunks}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteDoc(doc.doc_id);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-red-100 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area - PDF Viewer */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              {currentDoc ? (
                <>
                  <h2 className="text-lg font-semibold text-gray-900 truncate">{currentDoc.filename}</h2>
                  <p className="text-sm text-gray-500">
                    {currentDoc.total_chunks} chunks · {currentDoc.text_chunks} text · {currentDoc.code_chunks} code
                  </p>
                </>
              ) : (
                <>
                  <h2 className="text-lg font-semibold text-gray-900">Welcome to RAG Docs</h2>
                  <p className="text-sm text-gray-500">Upload a document to start viewing and querying</p>
                </>
              )}
            </div>
            <button
              onClick={() => setShowQuerySidebar(!showQuerySidebar)}
              className={`ml-4 px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                showQuerySidebar 
                  ? 'bg-blue-600 text-white hover:bg-blue-700' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              {showQuerySidebar ? 'Hide' : 'Show'} Query
            </button>
          </div>
        </div>

        {/* PDF Viewer, Text Viewer, or Empty State - Independent scroll area */}
        <div className="flex-1 overflow-hidden min-h-0">
          {currentDoc && pdfUrl ? (
            <PDFViewer fileUrl={pdfUrl} filename={currentDoc.filename} />
          ) : currentDoc && textContent ? (
            <TextViewer fileContent={textContent} filename={textFilename || currentDoc.filename} />
          ) : currentDoc ? (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <div className="text-center max-w-md px-4">
                <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-700 mb-2">Document Ready</h3>
                <p className="text-gray-500 mb-4">
                  {currentDoc.filename} has been uploaded and processed.
                </p>
                <p className="text-sm text-gray-400">
                  Use the query sidebar to ask questions about this document.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full bg-gradient-to-br from-blue-50 to-indigo-50">
              <div className="text-center max-w-md px-4">
                <Book className="w-20 h-20 text-blue-200 mx-auto mb-6" />
                <h3 className="text-2xl font-bold text-gray-800 mb-3">Get Started</h3>
                <p className="text-gray-600 mb-6">
                  Upload a document to view it in the PDF reader and query it with AI assistance.
                </p>
                  <label className="inline-block">
                    <input
                      ref={fileInputRef}
                      type="file"
                      onChange={handleFileUpload}
                      accept={ACCEPT_TYPES}
                      className="hidden"
                      disabled={uploading}
                    />
                  <div className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors shadow-lg">
                    <FileUp className="w-5 h-5" />
                    Upload Your First Document
                  </div>
                </label>
                <div className="mt-6">
                  <p className="text-sm font-semibold text-gray-700 mb-3">Supported Document Types:</p>
                  <div className="flex flex-wrap gap-3 justify-center">
                    {SUPPORTED_TYPES.map((type, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg shadow-sm border border-gray-200"
                      >
                        <span className="text-lg">{type.icon}</span>
                        <span className="text-sm font-medium text-gray-700">{type.name}</span>
                        <span className="text-xs text-gray-500">({type.ext})</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Sidebar - Query Assistant */}
      {showQuerySidebar && (
        <QuerySidebar
          currentDoc={currentDoc}
          isOpen={showQuerySidebar}
          onClose={() => setShowQuerySidebar(false)}
        />
      )}
    </div>
  );
}
