
"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, X, Bot, User, Loader2, RotateCcw } from "lucide-react";
import axios from "axios";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatAssistantProps {
  context?: {
    trust_score: number;
    risk: string;
    findings: string;
  };
}

const API_BASE = "http://localhost:8000/api";

export default function ChatAssistant({ context }: ChatAssistantProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        messages: [...messages, userMessage],
        context: context
      });

      const assistantMessage: Message = {
        role: "assistant",
        content: response.data.content
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Chat Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I'm sorry, I'm having trouble connecting to the fraud detection engine right now. Please try again later." }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 p-4 bg-blue-600 text-white rounded-full shadow-xl shadow-blue-200 hover:bg-blue-700 transition-all z-50 flex items-center gap-2 group"
        >
          <MessageSquare className="w-6 h-6" />
          <span className="max-w-0 overflow-hidden group-hover:max-w-[150px] transition-all font-bold whitespace-nowrap">Kavach Assistant</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-[400px] h-[600px] bg-white rounded-3xl shadow-2xl border border-slate-200 flex flex-col z-50 overflow-hidden transition-all animate-in slide-in-from-bottom-10">
          {/* Header */}
          <header className="p-4 bg-blue-600 text-white flex items-center justify-between shadow-md">
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-xl">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest leading-tight">Kavach AI</h3>
                <p className="text-[10px] text-blue-100 font-bold">Fraud Detection Expert</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setMessages([])} 
                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                title="Clear Chat"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setIsOpen(false)} 
                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </header>

          {/* Messages Area */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-slate-50/50">
            {messages.length === 0 && (
              <div className="text-center py-10 px-6 space-y-4">
                <div className="bg-blue-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto">
                  <Bot className="w-8 h-8 text-blue-500" />
                </div>
                <div>
                  <p className="font-bold text-slate-800">How can I help you today?</p>
                  <p className="text-xs text-slate-500 mt-1">I can explain analysis results, identify fraud markers, and guide you on next steps.</p>
                </div>
                {context && (
                  <div className="bg-white p-3 rounded-xl border border-blue-100 text-left">
                    <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">Current Context</p>
                    <p className="text-[11px] text-slate-600 font-bold">Document Analyzed: {context.trust_score}% Trust · {context.risk} Risk</p>
                  </div>
                )}
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={cn("flex items-start gap-2", msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
                <div className={cn("p-1.5 rounded-lg", msg.role === "user" ? "bg-slate-200" : "bg-blue-100")}>
                  {msg.role === "user" ? <User className="w-3.5 h-3.5 text-slate-600" /> : <Bot className="w-3.5 h-3.5 text-blue-600" />}
                </div>
                <div className={cn(
                  "max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed",
                  msg.role === "user" ? "bg-blue-600 text-white rounded-tr-none shadow-md shadow-blue-100" : "bg-white border border-slate-200 text-slate-700 rounded-tl-none shadow-sm"
                )}>
                  {msg.content}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start gap-2">
                <div className="p-1.5 rounded-lg bg-blue-100">
                  <Bot className="w-3.5 h-3.5 text-blue-600" />
                </div>
                <div className="bg-white border border-slate-200 p-3 rounded-2xl rounded-tl-none flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" />
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-slate-100 bg-white">
            <div className="relative flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Ask Kavach AI..."
                className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all placeholder:text-slate-400 font-medium"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="absolute right-2 p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-30 transition-all shadow-md shadow-blue-100"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
