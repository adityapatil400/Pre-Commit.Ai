import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  X,
  Bot,
  User,
  Copy,
  Check,
  Loader2,
  Trash2,
  HelpCircle,
  Lightbulb,
} from 'lucide-react';
import { ChatMessage } from '../../../types/playground';

interface VSCodeAIAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  onSendMessage: (prompt: string) => Promise<void>;
  isGenerating: boolean;
  activeFileName: string;
}

export const VSCodeAIAssistant: React.FC<VSCodeAIAssistantProps> = ({
  isOpen,
  onClose,
  messages,
  onSendMessage,
  isGenerating,
  activeFileName,
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || isGenerating) return;
    setInput('');
    await onSendMessage(prompt);
  };

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      setCopiedId(null);
    }
  };

  const quickPrompts = [
    'Why is this resource leak happening?',
    'Explain the current error in simple language',
    'Optimize this Python code for performance',
    'Add comprehensive type hints and docstrings',
  ];

  return (
    <div className="w-80 md:w-96 bg-[#252526] border-l border-[#1e1e1e] flex flex-col h-full text-[#cccccc] select-none z-10 shrink-0">
      {/* Assistant Header */}
      <div className="h-9 px-3 border-b border-[#2d2d2d] bg-[#252526] flex items-center justify-between text-[11px] font-bold tracking-wider uppercase">
        <div className="flex items-center gap-1.5 text-[#007acc]">
          <Sparkles className="w-3.5 h-3.5" />
          <span>PreCommit AI Assistant</span>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded text-[#858585] hover:text-white hover:bg-[#333333] transition-colors"
          title="Close AI Assistant"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 font-sans text-[12.5px]">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-8 text-center text-[#858585] space-y-3">
            <div className="w-10 h-10 rounded-full bg-[#1e1e1e] border border-[#333333] flex items-center justify-center text-[#007acc]">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-white">Ask PreCommit AI</p>
              <p className="text-[11.5px] text-[#777777] mt-0.5 max-w-xs">
                Contextual assistant powered by Ollama. Analyzes `{activeFileName}` and explains AST findings.
              </p>
            </div>

            {/* Quick Prompts */}
            <div className="w-full space-y-1.5 pt-2 text-left">
              <span className="text-[10.5px] font-bold text-[#666666] uppercase tracking-wider">
                Suggested questions:
              </span>
              {quickPrompts.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSendMessage(q)}
                  className="w-full text-left p-2 rounded bg-[#1e1e1e] hover:bg-[#2e2e2e] border border-[#333333] text-[11.5px] text-[#cccccc] transition-colors flex items-center justify-between group"
                >
                  <span className="truncate">{q}</span>
                  <Lightbulb className="w-3 h-3 text-[#007acc] opacity-0 group-hover:opacity-100 shrink-0 ml-1" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-center gap-1.5 mb-1 text-[10.5px] text-[#858585]">
                  {isUser ? (
                    <>
                      <span>You</span>
                      <User className="w-3 h-3 text-[#58a6ff]" />
                    </>
                  ) : (
                    <>
                      <Bot className="w-3 h-3 text-[#007acc]" />
                      <span>{msg.model || 'PreCommit AI'}</span>
                    </>
                  )}
                  <span>• {msg.timestamp}</span>
                </div>

                <div
                  className={`relative p-3 rounded-[8px] text-[12px] leading-relaxed max-w-[95%] select-text ${
                    isUser
                      ? 'bg-[#0e639c] text-white rounded-tr-none'
                      : 'bg-[#1e1e1e] border border-[#333333] text-[#d4d4d4] rounded-tl-none'
                  }`}
                >
                  {!isUser && (
                    <button
                      type="button"
                      onClick={() => handleCopy(msg.id, msg.content)}
                      className="absolute top-2 right-2 p-1 rounded text-[#858585] hover:text-white hover:bg-[#2d2d2d]"
                      title="Copy message"
                    >
                      {copiedId === msg.id ? (
                        <Check className="w-3 h-3 text-[#89d185]" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  )}

                  <div className="whitespace-pre-wrap font-sans space-y-1">
                    {msg.content}
                  </div>
                </div>
              </div>
            );
          })
        )}

        {isGenerating && (
          <div className="flex items-center gap-2 p-3 rounded bg-[#1e1e1e] border border-[#333333] text-[#858585] text-[12px]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#007acc]" />
            <span>PreCommit AI is thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-[#2d2d2d] bg-[#1e1e1e] space-y-2">
        <div className="relative">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                handleSubmit(e);
              }
            }}
            placeholder={`Ask about ${activeFileName}... (Ctrl+Enter)`}
            className="w-full bg-[#2d2d2d] text-white text-[12px] p-2 pr-8 rounded outline-none border border-transparent focus:border-[#007acc] resize-none"
          />

          <button
            type="submit"
            disabled={!input.trim() || isGenerating}
            className="absolute right-2 bottom-2.5 p-1 rounded bg-[#007acc] hover:bg-[#0062a3] text-white disabled:opacity-30 transition-all shadow-xs"
          >
            <Send className="w-3 h-3" />
          </button>
        </div>
      </form>
    </div>
  );
};

