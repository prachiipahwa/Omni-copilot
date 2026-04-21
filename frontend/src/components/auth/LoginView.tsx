"use client";

import { useAuth } from "@/context/AuthContext";
import { Database, LogIn } from "lucide-react";

export function LoginView() {
  const { loginWithGoogle } = useAuth();

  return (
    <div className="min-h-screen w-full bg-slate-950 flex flex-col items-center justify-center p-4 selection:bg-indigo-500/30">
      
      {/* Decorative background blur */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/20 rounded-full blur-[128px] pointer-events-none"></div>

      <div className="relative z-10 w-full max-w-md">
        
        {/* Card Header & Icon */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-16 h-16 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/20 mb-6">
            <Database size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Omni Copilot</h1>
          <p className="text-slate-400">Enterprise Unified AI Interface</p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-white mb-2">Welcome Back</h2>
            <p className="text-sm text-slate-400">Sign in to access your secure workspace.</p>
          </div>

          <button 
            onClick={loginWithGoogle}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 text-slate-900 py-3 px-4 rounded-xl font-medium transition-colors border border-transparent hover:border-slate-300"
          >
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="w-5 h-5" alt="Google logo" />
            Sign in with Google
          </button>
          
          <div className="mt-8 pt-6 border-t border-slate-800/50 flex justify-center text-xs text-slate-500 gap-4">
             <a href="#" className="hover:text-slate-300 transition-colors">Privacy</a>
             <a href="#" className="hover:text-slate-300 transition-colors">Terms</a>
             <a href="#" className="hover:text-slate-300 transition-colors">Security</a>
          </div>
        </div>
      </div>
    </div>
  );
}
