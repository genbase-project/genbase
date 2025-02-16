const DEFAULT_ENGINE_URL = import.meta.env.VITE_ENGINE_URL;

// Get stored engine URL or use default
export const ENGINE_BASE_URL = localStorage.getItem('engine_url') || DEFAULT_ENGINE_URL;

// Save engine URL to localStorage
export const setEngineUrl = (url: string) => {
  localStorage.setItem('engine_url', url);
  window.location.reload(); // Reload to apply new URL
};

// Get stored credentials
export const getAuthCredentials = () => {
  const stored = localStorage.getItem('auth_credentials');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return { username: '', password: '' };
    }
  }
  return { username: '', password: '' };
};

// Save credentials to localStorage
export const setAuthCredentials = (username: string, password: string) => {
  localStorage.setItem('auth_credentials', JSON.stringify({ username, password }));
};

type FetchOptions = RequestInit & {
  skipAuth?: boolean;
};

export const fetchWithAuth = async (url: string, options: FetchOptions = {}) => {
  const { skipAuth = false, ...fetchOptions } = options;

  if (!skipAuth) {
    const credentials = getAuthCredentials();
    const authHeader = btoa(`${credentials.username}:${credentials.password}`);
    fetchOptions.headers = {
      ...fetchOptions.headers,
      'Authorization': `Basic ${authHeader}`,
    };
  }

  const response = await fetch(url, fetchOptions);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response;
};
