"use client";

import { useState } from "react";
import { Database, Search, Sparkles } from "lucide-react";
import { FileText, Mail, Calendar, Loader2, AlertCircle, ExternalLink, RefreshCw, ServerCrash, CheckCircle2 } from "lucide-react";
import { ApiClient, ApiError } from "@/lib/api";

type TabType = "drive" | "gmail" | "calendar" | "index_status" | "search";

export default function KnowledgeBaseExplorer() {
  const [activeTab, setActiveTab] = useState<TabType>("index_status");
  const [data, setData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncNotice, setSyncNotice] = useState<{msg: string, stats?: any} | null>(null);
  
  // Search State
  const [query, setQuery] = useState("");
  const [searchSubmitted, setSearchSubmitted] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchContext, setSearchContext] = useState<string>("");

  const fetchStatus = async () => {
    setActiveTab("index_status");
    setIsLoading(true);
    setError(null);
    try {
      const response = await ApiClient.get<any[]>('/indexing/status');
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to fetch Indexing status.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeepSync = async () => {
    setIsSyncing(true);
    setSyncNotice(null);
    try {
      const res = await ApiClient.post<any>('/indexing/sync/google', {});
      setSyncNotice({msg: "Map-Reduce embedding completed securely.", stats: res});
      if (activeTab === "index_status") fetchStatus();
    } catch (err) {
      if (err instanceof ApiError) setSyncNotice({msg: `Failed: ${err.detail}`});
      else setSyncNotice({msg: "A critical backend error occurred."});
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Clear previous results before new search
    setSearchResults([]);
    setSearchContext("");
    setSearchSubmitted(false);
    setIsLoading(true);
    setError(null);

    try {
      const [resSearch, resCtx] = await Promise.all([
        ApiClient.get<any>(`/search/query?q=${encodeURIComponent(query)}&k=5`),
        ApiClient.get<any>(`/search/context?q=${encodeURIComponent(query)}&k=5`)
      ]);
      setSearchResults(resSearch.results || []);
      setSearchContext(resCtx.context || "");
      setSearchSubmitted(true);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Semantic projection failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchData = async (tab: TabType) => {
    if (tab === "index_status") return fetchStatus();
    if (tab === "search") {
      setActiveTab("search");
      setData([]);
      return;
    }
    setActiveTab(tab);
    setIsLoading(true);
    setError(null);
    setData([]);

    try {
      const response = await ApiClient.get<any[]>(`/retrieval/google/${tab}?max_results=5`);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to fetch data from provider");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/40 p-6 md:p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto w-full">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">Knowledge Base & Orchestration</h1>
            <p className="text-slate-400 text-sm max-w-3xl">Validate your direct integration extractions, and manually sync them into the deep-vector indexing pipeline (ChromaDB).</p>
          </div>
          <button 
             onClick={handleDeepSync}
             disabled={isSyncing}
             className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-indigo-600/20"
          >
             {isSyncing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
             <span>Synchronize Vector Index</span>
          </button>
        </div>

        {syncNotice && (
           <div className={`mb-6 p-4 rounded-xl border flex items-start justify-between gap-4 ${syncNotice.stats ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
              <div className="flex items-center gap-3 text-sm">
                {syncNotice.stats ? <CheckCircle2 size={18} /> : <ServerCrash size={18} />}
                <span className="font-medium">{syncNotice.msg}</span>
              </div>
              {syncNotice.stats && (
                 <div className="flex gap-4 text-xs">
                    <span>Docs processed: {syncNotice.stats.documents_processed}</span>
                    <span>Vector chunks: {syncNotice.stats.chunks_indexed}</span>
                 </div>
              )}
           </div>
        )}

        {/* Diagnostic Tabs */}
        <div className="flex space-x-2 mb-6 border-b border-slate-800 pb-px overflow-x-auto">
          <button 
            onClick={() => fetchData("search")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === 'search' ? 'border-amber-500 text-amber-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            <Sparkles size={16} /> Semantic Search
          </button>
          <button 
            onClick={() => fetchData("index_status")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === 'index_status' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            <Database size={16} /> Indexing Status
          </button>
          <button 
            onClick={() => fetchData("drive")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === 'drive' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            <FileText size={16} /> Drive Files
          </button>
          <button 
            onClick={() => fetchData("gmail")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === 'gmail' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            <Mail size={16} /> Recent Emails
          </button>
          <button 
            onClick={() => fetchData("calendar")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === 'calendar' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            <Calendar size={16} /> Upcoming Events
          </button>
        </div>

        {/* Results Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl min-h-[400px] p-6 relative overflow-hidden">
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80 backdrop-blur-sm z-10 rounded-2xl">
              <Loader2 size={32} className="text-indigo-500 animate-spin mb-4" />
              <p className="text-sm text-slate-400 font-medium tracking-wide animate-pulse">Decrypting Tokens & Fetching Provider...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-3 mt-12">
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
                 <AlertCircle size={24} className="text-red-400" />
              </div>
              <p className="text-slate-300 font-medium tracking-tight">Provider Request Failed</p>
              <p className="text-slate-500 text-sm max-w-sm">{error}</p>
            </div>
          )}

          {!isLoading && !error && activeTab === "search" && (
             <div className="space-y-6">
                <form onSubmit={handleSemanticSearch} className="relative">
                   <Search size={18} className="absolute left-4 top-1/2 -mt-[9px] text-slate-400" />
                   <input 
                     type="text" 
                     value={query}
                     onChange={e => setQuery(e.target.value)}
                     placeholder="Search across Drive, Gmail, & Calendar semantically..." 
                     className="w-full bg-slate-950 border border-slate-700/50 rounded-xl py-4 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 transition-all placeholder:text-slate-600"
                   />
                   <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 px-4 py-2 rounded-lg text-xs font-semibold transition-colors">
                     SEARCH
                   </button>
                </form>

                {/* Zero-results empty state — only shown after a real search completes */}
                {searchSubmitted && searchResults.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
                    <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
                      <Search size={20} className="text-amber-400" />
                    </div>
                    <p className="text-slate-300 font-medium">No relevant chunks found</p>
                    <p className="text-slate-500 text-sm max-w-sm">
                      The query returned no results above the relevance threshold. Try rephrasing or syncing more content first.
                    </p>
                  </div>
                )}

                {searchResults.length > 0 && (
                   <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                     {/* Search Result Chunks */}
                     <div className="space-y-3">
                       <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1 border-b border-slate-800 pb-2">Vector Chunks ({searchResults.length})</h3>
                       {searchResults.map((r, i) => (
                          <div key={r.id || i} className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                             <div className="flex items-center justify-between mb-2">
                               <span className="text-xs font-semibold text-slate-300">{r.metadata?.title}</span>
                               <div className="flex items-center gap-2">
                                 {r.score !== undefined && (
                                   <span className="text-[10px] font-mono text-slate-500">{(r.score * 100).toFixed(0)}%</span>
                                 )}
                                 <span className="text-[10px] uppercase font-bold text-amber-500/80 tracking-widest bg-amber-500/10 px-2 py-0.5 rounded">{r.metadata?.provider_source}</span>
                               </div>
                             </div>
                             <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">{r.text}</p>
                          </div>
                       ))}
                     </div>
                     {/* Context Assembly Preview */}
                     <div className="h-full">
                       <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1 border-b border-slate-800 pb-2 mb-3">AI Context Prompt Preview</h3>
                       <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-y-auto max-h-[500px]">
                         {searchContext ? (
                           <pre className="text-xs text-emerald-400/80 font-mono whitespace-pre-wrap leading-relaxed">{searchContext}</pre>
                         ) : (
                           <p className="text-xs text-slate-600 italic">No context assembled — all chunks may have been filtered.</p>
                         )}
                       </div>
                     </div>
                   </div>
                )}
             </div>
          )}

          {!isLoading && !error && data.length === 0 && activeTab !== "search" && activeTab !== "index_status" && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-3 mt-20">
              <p className="text-slate-400 font-medium text-sm">Click a provider tab to initiate connection validation.</p>
            </div>
          )}

          {!isLoading && !error && data.length > 0 && activeTab === "index_status" && (
             <div className="space-y-3">
               <div className="flex items-center justify-between px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                 <span>Source Title</span>
                 <div className="flex gap-12 text-right">
                   <span className="w-20">Chunks</span>
                   <span className="w-24">Status</span>
                   <span className="w-32">Provider</span>
                 </div>
               </div>
               {data.map((item, i) => (
                  <div key={item.id} className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/30 flex items-center justify-between group">
                    <div className="flex items-center gap-3">
                       <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                          <FileText size={14} className="text-slate-400" />
                       </div>
                       <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors">{item.title || "Untitled Document"}</span>
                    </div>
                    <div className="flex items-center gap-12 text-sm text-right">
                       <span className="w-20 font-mono text-slate-400">{item.chunk_count}</span>
                       <span className="w-24 text-emerald-400 capitalize flex items-center justify-end gap-1"><CheckCircle2 size={12}/> {item.status}</span>
                       <span className="w-32 text-indigo-400 text-xs font-medium uppercase tracking-widest">{item.provider_source}</span>
                    </div>
                  </div>
               ))}
             </div>
          )}

          {!isLoading && !error && data.length > 0 && activeTab !== "index_status" && (
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.map((item, i) => (
                  <div key={item.id || i} className="p-5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-slate-600 transition-colors flex flex-col gap-3 group">
                    <div className="flex items-start justify-between">
                       <h3 className="text-sm font-semibold text-slate-200 line-clamp-1 flex-1">
                         {item.name || item.subject || item.summary || "Untitled"}
                       </h3>
                       {item.web_view_link || item.html_link ? (
                         <a href={item.web_view_link || item.html_link} target="_blank" rel="noreferrer" className="text-slate-500 hover:text-indigo-400 transition-colors">
                           <ExternalLink size={14} />
                         </a>
                       ) : null}
                    </div>

                    {item.mime_type && <span className="text-xs text-indigo-400 bg-indigo-500/10 self-start px-2 py-0.5 rounded-sm font-mono">{item.mime_type}</span>}
                    
                    {item.snippet && <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{item.snippet}</p>}
                    
                    {item.description && <p className="text-xs text-slate-400 line-clamp-2">{item.description}</p>}
                    
                    <div className="mt-auto pt-2 flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-700/50 uppercase tracking-wider font-semibold">
                      <span>{item.provider_source.replace('_', ' ')}</span>
                      {item.date && <span>{new Date(item.date).toLocaleDateString()}</span>}
                      {item.start_time && <span>{new Date(item.start_time).toLocaleString()}</span>}
                      {item.updated_at && <span>{new Date(item.updated_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
