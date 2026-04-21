import { Bell, Search, PanelLeft } from "lucide-react";

export function Topbar() {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/50 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <button 
          className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 md:hidden transition-colors"
          aria-label="Toggle Navigation Panel"
        >
          <PanelLeft size={20} />
        </button>
        <div className="hidden sm:flex items-center text-sm text-slate-400" aria-label="Environment Badge">
          <span className="bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700 font-mono text-xs">Environment: Development</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative hidden w-64 md:block">
          <Search className="absolute left-2.5 top-2.5 text-slate-500" size={16} aria-hidden="true" />
          <input 
            type="text" 
            placeholder="Search across integrations..." 
            className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-full pl-9 pr-4 py-2 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-500"
            aria-label="Global Search"
          />
        </div>
        <button className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <div 
          className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 border-2 border-slate-800 shadow-md"
          role="img"
          aria-label="User Avatar"
        ></div>
      </div>
    </header>
  );
}
