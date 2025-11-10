"use client";

import { useAuth } from "@/contexts/AuthContext";
import { apiClient, AssistantQueryResponse, Citation, Project } from "@/lib/api";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  metadata?: AssistantQueryResponse["metadata"];
  timestamp: Date;
}

export default function AssistantPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [querying, setQuerying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const loadProject = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getProject(id);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
      if (err instanceof Error && err.message.includes("404")) {
        router.push("/projects");
      }
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    if (user && id) {
      loadProject();
    }
  }, [user, id, loadProject]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || querying) return;

    const question = input.trim();
    setInput("");
    setError(null);

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Query assistant
    setQuerying(true);
    try {
      const response = await apiClient.queryAssistant({
        project_id: id,
        question,
        top_k: 5,
        include_citations: true,
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        metadata: response.metadata,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to get response from assistant";
      setError(errorMessage);
      
      // Add error message to chat
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Sorry, I encountered an error: ${errorMessage}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setQuerying(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-600">Loading...</p>
      </div>
    );
  }

  if (!user || !project) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push(`/projects/${id}`)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                ← Back to Project
              </button>
              <h1 className="text-2xl font-bold text-gray-900">
                Marketing Copilot Assistant
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.email}</span>
              <button
                onClick={logout}
                className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-6 sm:px-6 lg:px-8">
        {/* Project Info Banner */}
        <div className="mb-4 rounded-lg bg-white p-4 shadow">
          <h2 className="text-lg font-semibold text-gray-900">{project.name}</h2>
          {project.description && (
            <p className="mt-1 text-sm text-gray-600">{project.description}</p>
          )}
          <p className="mt-2 text-xs text-gray-500">
            Ask questions about your project documents and get AI-powered answers with citations.
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto rounded-lg bg-white shadow">
          <div className="flex h-full flex-col p-6">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mb-4 text-6xl">🤖</div>
                  <h3 className="mb-2 text-xl font-semibold text-gray-900">
                    Welcome to the Assistant
                  </h3>
                  <p className="text-gray-600">
                    Ask me anything about your project documents. I'll search through your uploaded files and provide answers with citations.
                  </p>
                  <div className="mt-6 space-y-2 text-left">
                    <p className="text-sm font-medium text-gray-700">Try asking:</p>
                    <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                      <li>"What are the main topics covered in my documents?"</li>
                      <li>"Summarize the key points from my project files"</li>
                      <li>"What information do I have about [topic]?"</li>
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-3 ${
                        message.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                      </div>
                      
                      {/* Citations */}
                      {message.citations && message.citations.length > 0 && (
                        <div className={`mt-4 border-t pt-3 ${
                          message.role === "user" ? "border-white/20" : "border-gray-300"
                        }`}>
                          <p className={`mb-2 text-xs font-semibold ${
                            message.role === "user" ? "text-white/90" : "text-gray-700"
                          }`}>
                            📚 Sources ({message.citations.length}):
                          </p>
                          <div className="space-y-2">
                            {message.citations.map((citation, idx) => (
                              <div
                                key={idx}
                                className={`rounded p-2 text-xs ${
                                  message.role === "user"
                                    ? "bg-white/10 text-white"
                                    : "bg-gray-200 text-gray-800"
                                }`}
                              >
                                <div className="mb-1 font-semibold">
                                  [{citation.index}] Asset: {citation.asset_id.substring(0, 8)}...
                                </div>
                                <div className={`line-clamp-3 ${
                                  message.role === "user" ? "opacity-90" : "opacity-80"
                                }`}>
                                  "{citation.text}"
                                </div>
                                <div className={`mt-1 text-xs ${
                                  message.role === "user" ? "opacity-75" : "opacity-70"
                                }`}>
                                  Relevance: {(citation.score * 100).toFixed(1)}%
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Metadata */}
                      {message.metadata && (
                        <div className="mt-2 text-xs opacity-75">
                          <div className="flex gap-4">
                            <span>Model: {message.metadata.model}</span>
                            <span>Chunks: {message.metadata.chunks_retrieved}</span>
                            {message.metadata.has_context && (
                              <span className="text-green-300">✓ Context found</span>
                            )}
                          </div>
                        </div>
                      )}

                      <div className="mt-2 text-xs opacity-75">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                {querying && (
                  <div className="flex justify-start">
                    <div className="rounded-lg bg-gray-100 px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-75"></div>
                        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-150"></div>
                        <span className="ml-2 text-sm text-gray-600">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="mt-4">
          <div className="flex gap-2 rounded-lg bg-white p-4 shadow">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your project documents..."
              disabled={querying}
              rows={1}
              className="flex-1 resize-none rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              style={{
                minHeight: "44px",
                maxHeight: "200px",
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || querying}
              className="rounded-md bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {querying ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                  Sending...
                </span>
              ) : (
                "Send"
              )}
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </main>
    </div>
  );
}

