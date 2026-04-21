import { MessageResponse } from "@/types";

interface MessageBubbleProps {
  message: MessageResponse;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div 
        className={`max-w-3xl rounded-2xl px-5 py-4 shadow-sm ${
          isUser 
            ? 'bg-indigo-600 text-white rounded-br-none shadow-indigo-900/20' 
            : 'bg-slate-800 border border-slate-700 text-slate-200 rounded-bl-none shadow-black/10'
        }`}
        role="article"
        aria-label={`${isUser ? 'User' : 'Assistant'} message`}
      >
        <p className="text-sm md:text-base leading-relaxed tracking-wide whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}
