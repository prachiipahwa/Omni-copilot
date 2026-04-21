import { Send, Paperclip, Loader2 } from "lucide-react";
import { useState, KeyboardEvent, useRef, useEffect } from "react";

interface ChatInputProps {
  onSendMessage: (msg: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-4 md:p-6 bg-slate-900 border-t border-slate-800">
      <div className="max-w-4xl mx-auto relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl blur opacity-30 group-focus-within:opacity-100 transition duration-1000"></div>
        <div className="relative flex items-end gap-2 bg-slate-900 p-2 rounded-xl ring-1 ring-slate-800 shadow-xl">
          <button 
            type="button" 
            aria-label="Attach file"
            className="p-3 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <Paperclip size={20} />
          </button>
          
          <textarea 
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Omni Copilot..." 
            disabled={isLoading}
            className="w-full bg-transparent text-slate-200 placeholder:text-slate-500 text-base resize-none focus:outline-none py-3 disabled:opacity-50"
            rows={1}
            aria-label="Global Chat Input"
          />
          
          <button 
            type="button" 
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
            className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg transition-colors mb-0.5 mr-0.5"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
