// src/context/AuthContext.tsx
import React, { createContext, useState, useEffect, useContext, useCallback, ReactNode } from 'react';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config';
import { UserRead } from '@/types/schemas'; // Assuming you have this schema defined based on backend

interface AuthState {
  user: UserRead | null;
  isAuthenticated: boolean;
  isSuperuser: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserRead | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isSuperuser, setIsSuperuser] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUserData = useCallback(async () => {
    setIsLoading(true);
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setUser(null);
      setIsAuthenticated(false);
      setIsSuperuser(false);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/users/me`);
      if (response.ok) {
        const userData: UserRead = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
        setIsSuperuser(userData.is_superuser || false); // Ensure is_superuser exists
         console.log("User data fetched:", userData);
      } else {
        throw new Error('Failed to fetch user data');
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      localStorage.removeItem('auth_token');
      setUser(null);
      setIsAuthenticated(false);
      setIsSuperuser(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (token: string) => {
    localStorage.setItem('auth_token', token);
    await fetchUserData(); // Fetch user data immediately after login
  }, [fetchUserData]);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setUser(null);
    setIsAuthenticated(false);
    setIsSuperuser(false);
    // Redirect or handle post-logout logic here if needed
    window.location.href = '/login'; // Example redirect
  }, []);

  const checkAuth = useCallback(async () => {
     console.log("Checking auth status...");
     await fetchUserData();
  }, [fetchUserData]);


  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isSuperuser, isLoading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthState => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};