"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  MessageSquare, LayoutGrid, Plug, Settings,
  LogOut, Database, ChevronRight,
} from "lucide-react";

const NAV_LINKS = [
  { href: "/chat",         label: "Chat",           icon: MessageSquare },
  { href: "/knowledge",    label: "Knowledge Base",  icon: LayoutGrid   },
  { href: "/integrations", label: "Integrations",    icon: Plug         },
];

const BOTTOM_LINKS = [
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <aside
      className="w-60 bg-slate-900 border-r border-slate-800 hidden md:flex flex-col h-full flex-shrink-0"
      aria-label="Main Navigation"
    >
      {/* Logo */}
      <div className="p-4 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
          <Database size={15} className="text-white" />
        </div>
        <span className="font-bold text-white text-sm tracking-tight">Omni Copilot</span>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group
                ${active
                  ? "bg-indigo-500/15 text-indigo-300 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={16} className={active ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-400"} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={12} className="text-indigo-500/60" />}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section — settings + user */}
      <div className="p-3 border-t border-slate-800 space-y-0.5">
        {BOTTOM_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group
                ${active ? "bg-slate-800 text-slate-200" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"}`}
            >
              <Icon size={16} className="text-slate-500 group-hover:text-slate-400" />
              {label}
            </Link>
          );
        })}

        {/* User identity row */}
        {user && (
          <div className="flex items-center gap-2.5 px-3 py-2 mt-1">
            <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
              <span className="text-[10px] font-bold text-indigo-300 uppercase">
                {(user.name || user.email)?.[0] ?? "U"}
              </span>
            </div>
            <span className="text-xs text-slate-500 truncate flex-1">
              {user.name || user.email}
            </span>
          </div>
        )}

        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
        >
          <LogOut size={15} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
