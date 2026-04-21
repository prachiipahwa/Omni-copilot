"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

/**
 * Root page — redirects authenticated users to /chat,
 * unauthenticated users to the login screen.
 * Shows a clean spinner while auth state resolves.
 */
export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (user) {
      router.replace("/chat");
    } else {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex h-full items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-4">
        <Loader2 size={28} className="animate-spin text-indigo-400" />
        <p className="text-slate-500 text-sm">Loading Omni Copilot…</p>
      </div>
    </div>
  );
}
