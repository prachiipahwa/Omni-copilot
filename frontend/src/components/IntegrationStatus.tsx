"use client";

import { ServerCrash, Cloud, PlugZap, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiClient } from "@/lib/api";
import { IntegrationStatusResponse } from "@/types";

export function IntegrationStatus() {
  const [statuses, setStatuses] = useState<IntegrationStatusResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const data = await ApiClient.get<IntegrationStatusResponse[]>('/integrations/status');
        setStatuses(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch status');
      } finally {
        setIsLoading(false);
      }
    }
    fetchStatus();
  }, []);

  return (
    <div className="w-80 border-l border-slate-800 bg-slate-900 hidden lg:flex flex-col h-full" aria-label="Integrations Status Panel">
      <div className="p-4 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Cloud size={16} className="text-indigo-400" />
          Active Connections
        </h3>
      </div>
      <div className="p-4 space-y-3 flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-6 text-slate-500">
             <Loader2 className="animate-spin" size={24} />
          </div>
        ) : error ? (
          <div className="text-xs text-red-400 bg-red-400/10 p-3 rounded-md border border-red-500/20 flex gap-2 items-center">
             <ServerCrash size={14} />
             {error}
          </div>
        ) : statuses.length === 0 ? (
          <div className="text-xs text-slate-400 text-center py-6">No integrations available.</div>
        ) : (
          statuses.map((status) => (
            <div key={status.provider} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 transition-colors">
              <div className="flex items-center gap-2 text-slate-200 font-medium text-sm capitalize">
                {status.provider.replace('_', ' ')}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{status.status_label}</span>
                <div 
                  className={`w-2 h-2 rounded-full ${status.is_connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-600'}`}
                  title={status.status_label}
                />
              </div>
            </div>
          ))
        )}
        
        <button 
          className="mt-6 w-full border border-dashed border-slate-700 rounded-lg p-4 flex flex-col items-center justify-center text-center gap-2 hover:bg-slate-800 hover:border-slate-600 transition-colors cursor-pointer group focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Add new integration"
        >
           <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center group-hover:bg-slate-700 group-hover:scale-110 transition-all shadow-inner">
              <PlugZap size={14} className="text-slate-400 group-hover:text-indigo-400" />
           </div>
           <span className="text-xs font-medium text-slate-400 group-hover:text-slate-300">Add Integration</span>
        </button>
      </div>
    </div>
  );
}
