import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from "@/components/themeProvider"
import { AuthPage } from '@/components/AuthPage'
import { getAuthCredentials } from './config.ts'

function Root() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const credentials = getAuthCredentials();
    setIsAuthenticated(!!credentials.username && !!credentials.password);
  }, []);

  if (!isAuthenticated) {
    return (
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <AuthPage onAuthSuccess={() => setIsAuthenticated(true)} />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <App />
    </ThemeProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
