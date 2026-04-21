"use client";

import { AuthProvider, useAuth } from "@/context/AuthContext";
import { LoginView } from "@/components/auth/LoginView";
import { Loader2 } from "lucide-react";

function AuthRenderer({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-slate-950">
         <Loader2 size={32} className="text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <LoginView />;
  }

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
       <AuthRenderer>{children}</AuthRenderer>
    </AuthProvider>
  );
}
