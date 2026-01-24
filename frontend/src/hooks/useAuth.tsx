import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiClient } from '@/lib/api';

interface User {
  id: string;
  username?: string;
  email?: string;
  full_name?: string;
  github_connected: boolean;
  linkedin_connected: boolean;
  github_username?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  guestId: string;
  loading: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (userData: { username: string; email: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuthStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [guestId, setGuestId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const refreshAuthStatus = async () => {
    try {
      setLoading(true);
      const status = await apiClient.getAuthStatus();
      
      if (status.authenticated && status.user) {
        setUser(status.user);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
      
      setGuestId(status.guest_id);
    } catch (error) {
      console.error('Failed to get auth status:', error);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials: { email: string; password: string }) => {
    try {
      await apiClient.login(credentials);
      await refreshAuthStatus();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (userData: { username: string; email: string; password: string; full_name?: string }) => {
    try {
      await apiClient.register(userData);
      await refreshAuthStatus();
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiClient.logout();
      setUser(null);
      setIsAuthenticated(false);
      await refreshAuthStatus(); // Get new guest ID
    } catch (error) {
      console.error('Logout failed:', error);
      // Clear local state anyway
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  useEffect(() => {
    // Check authentication status on mount
    refreshAuthStatus();
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    guestId,
    loading,
    login,
    register,
    logout,
    refreshAuthStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};