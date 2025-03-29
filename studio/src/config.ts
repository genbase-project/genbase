// Constants
const DEFAULT_ENGINE_URL = import.meta.env.VITE_ENGINE_URL || 'http://localhost:8000';

// Get stored engine URL or use default
export const ENGINE_BASE_URL = localStorage.getItem('engine_url') || DEFAULT_ENGINE_URL;

// Save engine URL to localStorage
export const setEngineUrl = (url: string) => {
  localStorage.setItem('engine_url', url);
  window.location.reload(); // Reload to apply new URL
};

// Fetch with auth token (JWT)
export const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('auth_token');
  
  // Include authorization header if token exists
  const headers = token 
    ? { ...options.headers, 'Authorization': `Bearer ${token}` }
    : options.headers;

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response;
};

// Simple logout function
export const logout = () => {
  localStorage.removeItem('auth_token');
  
  // You can redirect to login page if needed
  // window.location.href = '/login';
  
  // Or refresh the page if your app handles auth state
  // window.location.reload();
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!localStorage.getItem('auth_token');
};