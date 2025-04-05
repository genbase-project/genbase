// main.tsx or index.tsx (assuming this structure)
import { StrictMode, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom'; // Import BrowserRouter
import './index.css';
import App from './App.tsx';
import { ThemeProvider } from "@/components/themeProvider";
import { AuthPage } from '@/components/AuthPage';
import { isAuthenticated } from './config.ts';
import { AuthProvider } from './context/AuthContext.tsx';

function Root() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setIsLoggedIn(isAuthenticated());
    setLoading(false);
  }, []);

  // Show loading state (optional)
  if (loading) {
    return (
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <div className="min-h-screen flex items-center justify-center">
          <p>Loading...</p>
        </div>
      </ThemeProvider>
    );
  }

  // Show auth page if not logged in
  if (!isLoggedIn) {
    return (
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <AuthPage onAuthSuccess={() => setIsLoggedIn(true)} />
      </ThemeProvider>
    );
  }

  // Show main app if logged in
  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      {/* Wrap App with BrowserRouter */}
      <BrowserRouter>
      <AuthProvider> 
        <App />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);