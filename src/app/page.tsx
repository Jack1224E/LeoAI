"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Menu, MessageSquare, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [model, setModel] = useState("jlm");
  const [isDeepthink, setIsDeepthink] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMessage].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          model,
          isDeepthink,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const assistantContent =
        data.choices?.[0]?.message?.content || "No response.";

      const assistantMessage: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: assistantContent,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", backgroundColor: "var(--background)" }}>
      {/* Sidebar */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: "260px", opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="glass"
            style={{
              height: "100%",
              borderRight: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              flexShrink: 0,
            }}
          >
            <div style={{ padding: "20px", display: "flex", alignItems: "center", gap: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
              <div style={{
                width: "32px", height: "32px", borderRadius: "8px",
                background: "linear-gradient(135deg, var(--accent-cyan), var(--accent))",
                display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: "bold"
              }}>
                J
              </div>
              <h1 className="gradient-text" style={{ fontSize: "1.25rem", fontWeight: "bold" }}>Jack AI</h1>
            </div>

            <div style={{ flex: 1, padding: "16px", overflowY: "auto" }}>
              <button
                onClick={() => { setMessages([]); setError(null); }}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: "12px", padding: "12px",
                  borderRadius: "8px", backgroundColor: "var(--surface-2)", color: "var(--foreground)",
                  border: "1px solid var(--border-strong)", cursor: "pointer", transition: "0.2s"
                }}
              >
                <MessageSquare size={18} />
                <span style={{ fontSize: "0.875rem" }}>New Chat</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Header */}
        <header style={{
          height: "64px", display: "flex", alignItems: "center", padding: "0 20px",
          borderBottom: "1px solid var(--border-subtle)", backgroundColor: "rgba(5, 5, 7, 0.8)",
          backdropFilter: "blur(12px)", zIndex: 10
        }}>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", marginRight: "16px" }}
          >
            <Menu size={20} />
          </button>

          <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.875rem", color: "var(--foreground)", cursor: "pointer", userSelect: "none" }}>
              <input 
                type="checkbox" 
                checked={isDeepthink} 
                onChange={(e) => setIsDeepthink(e.target.checked)} 
                style={{ cursor: "pointer", accentColor: "var(--accent-cyan)" }}
              />
              <span style={{ fontWeight: isDeepthink ? "bold" : "normal", color: isDeepthink ? "var(--accent-cyan)" : "var(--foreground)" }}>Deepthink</span>
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{
                padding: "6px 12px", borderRadius: "6px", backgroundColor: "var(--surface-1)",
                border: "1px solid var(--border-strong)", color: "var(--foreground)", outline: "none",
                fontSize: "0.875rem"
              }}
            >
              <option value="jlm">JLM (Jack Language Model)</option>
            </select>
          </div>
        </header>

        {/* Chat Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", display: "flex", flexDirection: "column", gap: "24px" }}>
          {messages.length === 0 ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "16px" }}>
              <div style={{ width: "64px", height: "64px", borderRadius: "16px", background: "var(--surface-2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Bot size={32} color="var(--accent-cyan)" />
              </div>
              <h2 style={{ fontSize: "1.5rem", color: "var(--muted)" }}>How can I help you today?</h2>
            </div>
          ) : (
            messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  display: "flex",
                  gap: "16px",
                  maxWidth: "800px",
                  margin: "0 auto",
                  width: "100%",
                }}
              >
                <div style={{
                  width: "36px", height: "36px", borderRadius: "8px", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  backgroundColor: m.role === "user" ? "var(--surface-2)" : "var(--accent-glow)",
                  color: m.role === "user" ? "var(--foreground)" : "var(--accent-cyan)"
                }}>
                  {m.role === "user" ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div style={{ flex: 1, paddingTop: "6px" }}>
                  <div style={{ fontSize: "0.95rem", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                    {m.content}
                  </div>
                </div>
              </motion.div>
            ))
          )}

          {error && (
            <div style={{ maxWidth: "800px", margin: "0 auto", width: "100%", color: "#ef4444", padding: "12px", backgroundColor: "rgba(239, 68, 68, 0.1)", borderRadius: "8px" }}>
              Error: {error}
            </div>
          )}

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: "flex", gap: "16px", maxWidth: "800px", margin: "0 auto", width: "100%" }}
            >
              <div style={{
                width: "36px", height: "36px", borderRadius: "8px", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                backgroundColor: "var(--accent-glow)", color: "var(--accent-cyan)"
              }}>
                <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} />
              </div>
              <div style={{ flex: 1, paddingTop: "10px", fontSize: "0.875rem", color: "var(--muted)" }}>
                Thinking...
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{ padding: "0 20px 24px", maxWidth: "840px", margin: "0 auto", width: "100%" }}>
          <form onSubmit={handleSubmit} style={{ position: "relative" }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Jack AI..."
              disabled={isLoading}
              style={{
                width: "100%",
                padding: "16px 48px 16px 20px",
                borderRadius: "16px",
                backgroundColor: "var(--surface-1)",
                border: "1px solid var(--border-strong)",
                color: "var(--foreground)",
                fontSize: "1rem",
                outline: "none",
                boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
              }}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              style={{
                position: "absolute",
                right: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                background: input.trim() ? "var(--accent)" : "var(--surface-2)",
                border: "none",
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: input.trim() ? "white" : "var(--muted)",
                cursor: input.trim() ? "pointer" : "default",
                transition: "0.2s"
              }}
            >
              <Send size={16} />
            </button>
          </form>
          <div style={{ textAlign: "center", marginTop: "8px", fontSize: "0.75rem", color: "var(--muted)", opacity: 0.7 }}>
            Jack AI — Advanced Architectural Intelligence
          </div>
        </div>
      </div>
    </div>
  );
}