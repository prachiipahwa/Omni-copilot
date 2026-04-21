"use client";

import React, {
  useState, useRef, useEffect, useCallback, memo, useMemo,
} from "react";
import {
  Send, Loader2, AlertCircle, Bot, User, Sparkles,
  FileText, Mail, Calendar, ExternalLink, RefreshCw,
  Copy, Check, RotateCcw, ArrowDown,
} from "lucide-react";
import { ApiClient, ApiError } from "@/lib/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const MAX_INPUT_CHARS = 4000;

// ── Types ─────────────────────────────────────────────────────────────────────

interface SourceCitation {
  id: string;
  title: string;
  provider: string;
  url?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  tools_used?: string[];
  sources?: SourceCitation[];
  fallback?: boolean;
  latency_ms?: number;
  failed?: boolean;
}

interface SendResponse {
  session_id: string;
  message_id: string;
  answer: string;
  intent: string;
  tools_used: string[];
  sources: SourceCitation[];
  fallback: boolean;
  latency_ms: number;
}

const INTENT_LABELS: Record<string, string> = {
  semantic_search: "Vector Search",
  email_recent:    "Email",
  calendar:        "Calendar",
  drive_search:    "Drive",
  grounded_answer: "RAG",
  plain_chat:      "Chat",
};

const SUGGESTIONS = [
  "Summarize my recent emails",
  "What meetings do I have today?",
  "Find notes about the Q1 roadmap",
  "What documents did I share last week?",
];

// ── Memoized Sub-components ────────────────────────────────────────────────────

function ProviderIcon({ provider, size = 11 }: { provider: string; size?: number }) {
  if (provider === "gmail")           return <Mail size={size} />;
  if (provider === "google_calendar") return <Calendar size={size} />;
  return <FileText size={size} />;
}

const SourceCard = memo(({ source }: { source: SourceCitation }) => {
  const hasUrl = Boolean(source.url?.trim());
  const cls =
    "inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium border transition-colors " +
    "bg-slate-800/60 border-slate-700/50 text-slate-300 hover:border-indigo-500/40 hover:text-white";
  const inner = (
    <>
      <span className="text-indigo-400"><ProviderIcon provider={source.provider} /></span>
      <span className="max-w-[140px] truncate">{source.title}</span>
      {hasUrl && <ExternalLink size={9} className="text-slate-500 flex-shrink-0" />}
    </>
  );

  return hasUrl ? (
    <a href={source.url} target="_blank" rel="noopener noreferrer" className={cls}>{inner}</a>
  ) : (
    <span className={cls}>{inner}</span>
  );
});
SourceCard.displayName = "SourceCard";

const CopyButton = memo(({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} title="Copy response" className="p-1.5 rounded-md text-slate-600 hover:text-slate-300 hover:bg-slate-700/50 transition-colors">
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
    </button>
  );
});
CopyButton.displayName = "CopyButton";

const IntentBadge = memo(({ intent }: { intent: string }) => (
  <span className="inline-flex items-center text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/10">
    {INTENT_LABELS[intent] ?? intent}
  </span>
));
IntentBadge.displayName = "IntentBadge";

const MessageBubble = memo(({ msg, onRetry }: { msg: ChatMessage; onRetry?: (content: string) => void }) => {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} group animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border ${isUser ? "bg-indigo-600 border-indigo-500 shadow-lg shadow-indigo-600/20" : "bg-slate-800 border-slate-700"}`}>
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-indigo-400" />}
      </div>
      <div className={`max-w-[85%] sm:max-w-[70%] flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words shadow-sm ${isUser ? "bg-indigo-600 text-white rounded-tr-sm" : msg.failed ? "bg-red-500/10 border border-red-500/20 text-red-300 rounded-tl-sm" : "bg-slate-800/80 border border-slate-700/50 text-slate-200 rounded-tl-sm"}`}>
          {msg.content}
        </div>
        {!isUser && !msg.failed && (
          <div className="flex flex-col gap-1.5 pl-1 w-full opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <div className="flex flex-wrap items-center gap-2">
              {msg.intent && <IntentBadge intent={msg.intent} />}
              {msg.tools_used && msg.tools_used.length > 0 && <span className="text-[10px] text-slate-500">via {msg.tools_used.join(" + ")}</span>}
              {msg.latency_ms !== undefined && <span className="text-[10px] text-slate-700">{msg.latency_ms}ms</span>}
              {msg.fallback && <span className="text-[10px] text-amber-400 font-semibold italic">⚠ partial data</span>}
              <span className="ml-auto"><CopyButton text={msg.content} /></span>
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-0.5">
                {msg.sources.map((s) => <SourceCard key={s.id} source={s} />)}
              </div>
            )}
          </div>
        )}
        {!isUser && msg.failed && onRetry && (
          <button onClick={() => onRetry(msg.content)} className="flex items-center gap-1.5 text-[11px] text-red-400 hover:text-red-300 transition-colors pl-1 mt-0.5">
            <RotateCcw size={11} /> Retry
          </button>
        )}
      </div>
    </div>
  );
});
MessageBubble.displayName = "MessageBubble";

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string>("");

  // Safety: Abort pending requests on unmount
  useEffect(() => () => abortControllerRef.current?.abort(), []);

  // Scroll logic
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    bottomRef.current?.scrollIntoView({ behavior });
  }, []);

  useEffect(() => {
    if (isAtBottom) scrollToBottom();
  }, [messages, isLoading, isAtBottom, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const isBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 100;
    setIsAtBottom(isBottom);
  }, []);

  // Input resize
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [input]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    
    // Safety: Abort any current flight
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    const safeText = text.trim().slice(0, MAX_INPUT_CHARS);
    lastUserMessageRef.current = safeText;
    setInput("");
    setError(null);
    setIsAtBottom(true);

    const tempId = `user-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tempId, role: "user", content: safeText }]);
    setIsLoading(true);

    try {
      const response = await ApiClient.post<any, SendResponse>(
        "/chat/send", 
        { message: safeText, session_id: sessionId ?? undefined },
        { signal: abortControllerRef.current.signal }
      );

      if (!sessionId && response.session_id) setSessionId(response.session_id);
      setMessages((prev) => [...prev, {
        id: response.message_id,
        role: "assistant",
        content: response.answer,
        intent: response.intent,
        tools_used: response.tools_used,
        sources: response.sources,
        fallback: response.fallback,
        latency_ms: response.latency_ms,
      }]);
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      const detail = err instanceof ApiError ? err.detail : "Failed to reach AI. Check connection.";
      setError(detail);
      setMessages((prev) => [...prev, { id: `fail-${Date.now()}`, role: "assistant", content: detail, failed: true }]);
    } finally {
      setIsLoading(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isLoading, sessionId]);

  const handleNewSession = () => {
    if (isLoading && !window.confirm("Active request found. Start new session anyway?")) return;
    abortControllerRef.current?.abort();
    setSessionId(null);
    setMessages([]);
    setError(null);
    lastUserMessageRef.current = "";
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleRetry = useCallback(() => {
    setMessages((prev) => prev.filter((m) => !m.failed));
    sendMessage(lastUserMessageRef.current);
  }, [sendMessage]);

  return (
    <div className="flex flex-col h-full bg-slate-950 relative">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-slate-800 bg-slate-900/40 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
            <Sparkles size={15} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight">Omni Copilot</h1>
            <p className="text-[10px] text-slate-500 font-medium uppercase tracking-widest leading-none mt-1 opacity-70">
              {sessionId ? `ID: ${sessionId.slice(0, 8)}` : "Live Session"}
            </p>
          </div>
        </div>
        <button onClick={handleNewSession} className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 transition-all border border-transparent hover:border-slate-700" title="Reset Session">
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
        </button>
      </header>

      {/* Messages Area */}
      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-12 py-8 space-y-6 scroll-smooth custom-scrollbar">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 pt-12 animate-in fade-in duration-700">
             <div className="w-20 h-20 rounded-3xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center shadow-2xl shadow-indigo-600/5 rotate-3 hover:rotate-0 transition-transform duration-500">
               <Bot size={36} className="text-indigo-400" />
             </div>
             <div className="space-y-2">
               <h2 className="text-xl font-semibold text-slate-100">Intelligent Work Assistance</h2>
               <p className="text-slate-500 text-sm max-w-xs mx-auto leading-relaxed">
                 Access your Drive, Gmail, and Calendar via unified semantic retrieval.
               </p>
             </div>
             <div className="flex flex-wrap justify-center gap-2 max-w-md">
               {SUGGESTIONS.map(s => (
                 <button key={s} onClick={() => setInput(s)} className="text-xs px-4 py-2.5 rounded-xl border border-slate-800 text-slate-400 hover:border-indigo-500/40 hover:text-slate-100 hover:bg-slate-900/50 transition-all">
                   {s}
                 </button>
               ))}
             </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} onRetry={handleRetry} />
        ))}

        {isLoading && (
          <div className="flex gap-3 animate-in fade-in duration-500">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0">
               <Bot size={14} className="text-indigo-400" />
            </div>
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-2">
               {[0, 1, 2].map(i => (
                 <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
               ))}
            </div>
          </div>
        )}

        {error && !isLoading && (
          <div className="mx-auto max-w-fit flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
             <AlertCircle size={12} /> {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Floating Jump to Bottom */}
      {!isAtBottom && (
        <button onClick={() => scrollToBottom()} className="absolute bottom-32 right-8 p-2.5 rounded-full bg-indigo-600 border border-indigo-500 text-white shadow-xl hover:bg-indigo-500 transition-all animate-in zoom-in slide-in-from-bottom-4 duration-300">
          <ArrowDown size={18} />
        </button>
      )}

      {/* Input Overlay */}
      <div className="px-4 sm:px-6 md:px-12 pb-8 pt-2 bg-gradient-to-t from-slate-950 via-slate-950 to-transparent">
        <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="relative group max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, MAX_INPUT_CHARS))}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
            placeholder="Ask anything..."
            disabled={isLoading}
            className="w-full resize-none bg-slate-900/80 border border-slate-800 rounded-2xl pl-5 pr-14 py-4 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60 focus:ring-4 focus:ring-indigo-500/5 disabled:opacity-50 transition-all shadow-2xl"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-3 bottom-3 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 flex items-center justify-center transition-all shadow-lg active:scale-95"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin text-white" /> : <Send size={16} className="text-white" />}
          </button>
        </form>
        <div className="max-w-3xl mx-auto mt-2 flex justify-between items-center px-2">
           <span className="text-[10px] text-slate-700 font-medium uppercase tracking-tight">Shift+Enter for line break</span>
           {input.length > MAX_INPUT_CHARS * 0.8 && (
             <span className={`text-[10px] font-bold ${input.length >= MAX_INPUT_CHARS ? "text-red-500" : "text-amber-500"}`}>
               {input.length}/{MAX_INPUT_CHARS}
             </span>
           )}
        </div>
      </div>
    </div>
  );
}
