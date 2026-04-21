"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { ApiClient } from '@/lib/api';
import { Loader2 } from 'lucide-react';

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthContextType {
  user: UserResponse | null;
  isLoading: boolean;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  loginWithGoogle: async () => {},
  logout: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const data = await ApiClient.get<UserResponse>('/auth/me');
      setUser(data);
    } catch (e) {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async () => {
    try {
      const { authorization_url } = await ApiClient.get<{authorization_url: string}>('/auth/login/google');
      window.location.href = authorization_url;
    } catch (error) {
      console.error("Failed to fetch login URL", error);
    }
  };

  const logout = async () => {
    try {
      await ApiClient.post('/auth/logout', {});
      setUser(null);
      window.location.reload();
    } catch (error) {
      console.error("Failed to logout", error);
    }
  };

  // Hardening: Prevent UI flicker by providing a stable loading screen during initial boot
  if (isLoading) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-slate-950 text-slate-400 gap-4">
        <div className="relative">
             <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
             <div className="absolute inset-0 flex items-center justify-center">
                 <div className="w-6 h-6 rounded-full bg-indigo-500/10 blur-sm animate-pulse" />
             </div>
        </div>
        <p className="text-xs font-medium tracking-widest uppercase opacity-60">Initializing Copilot</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
