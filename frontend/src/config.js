// API configuration
// In production, this will be set by environment variables
// In development, it defaults to localhost:8000
// For Docker, use the backend service name if running in same network
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 
  (typeof window !== 'undefined' && window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : '/api');

