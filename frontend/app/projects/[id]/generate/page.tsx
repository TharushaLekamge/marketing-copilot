"use client";

import ContentVariants from "@/components/ContentVariants";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiClient,
  GenerationRequest,
  GenerationResponse,
  GenerationUpdateRequest,
  Project,
} from "@/lib/api";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";

export default function GeneratePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [polling, setPolling] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<"pending" | "processing" | "completed" | "failed" | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<GenerationResponse | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Form state
  const [brief, setBrief] = useState("");
  const [brandTone, setBrandTone] = useState("");
  const [audience, setAudience] = useState("");
  const [objective, setObjective] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [channelInput, setChannelInput] = useState("");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const loadProject = useCallback(async () => {
    try {
      setLoading(true);
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

  const pollGenerationStatus = async (genId: string) => {
    try {
      const result = await apiClient.getGenerationRecord(genId);
      
      // Check if content is available (status is completed)
      if (result.short_form || result.long_form || result.cta) {
        // Content is available - generation completed
        setResponse(result);
        setGenerationStatus("completed");
        setPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } else {
        // Still pending or processing - continue polling
        setGenerationStatus("processing");
      }
    } catch (err) {
      // Check if it's a failed generation error
      const errorMessage = err instanceof Error ? err.message : "Failed to check generation status";
      if (errorMessage.includes("Generation failed") || errorMessage.includes("failed")) {
        setGenerationStatus("failed");
        setError(errorMessage);
        setPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } else {
        // Other error - log but continue polling
        console.error("Error polling generation status:", err);
      }
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!brief.trim()) {
      setError("Brief is required");
      return;
    }

    try {
      setGenerating(true);
      setError(null);
      setResponse(null);
      setGenerationStatus(null);
      setGenerationId(null);

      // Clear any existing polling interval
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }

      const request: GenerationRequest = {
        project_id: id,
        brief: brief.trim(),
        brand_tone: brandTone.trim() || null,
        audience: audience.trim() || null,
        objective: objective.trim() || null,
        channels: channels.length > 0 ? channels : null,
      };

      // Submit generation request - returns 202 Accepted
      const acceptedResponse = await apiClient.generateContent(request);
      
      setGenerationId(acceptedResponse.generation_id);
      setGenerationStatus(acceptedResponse.status);
      setGenerating(false);
      setPolling(true);

      // Start polling for results
      // Poll immediately, then every 2 seconds
      pollGenerationStatus(acceptedResponse.generation_id);
      
      pollingIntervalRef.current = setInterval(() => {
        pollGenerationStatus(acceptedResponse.generation_id);
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate content");
      setGenerating(false);
      setPolling(false);
    }
  };

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleAddChannel = () => {
    if (channelInput.trim() && !channels.includes(channelInput.trim())) {
      setChannels([...channels, channelInput.trim()]);
      setChannelInput("");
    }
  };

  const handleRemoveChannel = (channel: string) => {
    setChannels(channels.filter((c) => c !== channel));
  };

  const handleEditVariant = async (variantType: string, content: string) => {
    if (!response || !response.generation_id) return;

    try {
      setUpdating(true);
      setError(null);
      setSuccessMessage(null);

      // Update local state immediately for better UX
      const updatedResponse: GenerationResponse = {
        ...response,
        short_form: variantType === "short_form" ? content : response.short_form,
        long_form: variantType === "long_form" ? content : response.long_form,
        cta: variantType === "cta" ? content : response.cta,
      };
      setResponse(updatedResponse);

      // Call API to save the update
      const updateRequest: GenerationUpdateRequest = {
        short_form: updatedResponse.short_form,
        long_form: updatedResponse.long_form,
        cta: updatedResponse.cta,
      };

      const result = await apiClient.updateGenerationRecord(response.generation_id, updateRequest);
      
      // Update with server response
      setResponse(result.updated);
      setSuccessMessage(result.message);

      // Clear success message after 3 seconds
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update content");
      // Revert to original response on error
      // Note: In a real app, you might want to keep the edited version and show a retry option
    } finally {
      setUpdating(false);
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
                Marketing Copilot
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

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        {/* Project Header */}
        <div className="mb-6 rounded-lg bg-white p-6 shadow">
          <h2 className="text-3xl font-bold text-gray-900">{project.name}</h2>
          {project.description && (
            <p className="mt-2 text-lg text-gray-600">{project.description}</p>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {successMessage && (
          <div className="mb-4 rounded-md bg-green-50 p-4">
            <p className="text-sm text-green-800">{successMessage}</p>
          </div>
        )}

        {!response && !polling ? (
          /* Generation Form */
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="mb-6 text-2xl font-bold text-gray-900">
              Generate Content
            </h3>

            <form onSubmit={handleGenerate} className="space-y-6">
              <div>
                <label
                  htmlFor="brief"
                  className="block text-sm font-medium text-gray-700"
                >
                  Campaign Brief <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="brief"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  required
                  rows={5}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  placeholder="Describe your campaign, what you want to promote, key messages, etc."
                />
              </div>

              <div>
                <label
                  htmlFor="brandTone"
                  className="block text-sm font-medium text-gray-700"
                >
                  Brand Tone
                </label>
                <input
                  type="text"
                  id="brandTone"
                  value={brandTone}
                  onChange={(e) => setBrandTone(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  placeholder="e.g., Professional, Friendly, Casual, Energetic"
                />
              </div>

              <div>
                <label
                  htmlFor="audience"
                  className="block text-sm font-medium text-gray-700"
                >
                  Target Audience
                </label>
                <input
                  type="text"
                  id="audience"
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  placeholder="e.g., Young professionals, Small business owners"
                />
              </div>

              <div>
                <label
                  htmlFor="objective"
                  className="block text-sm font-medium text-gray-700"
                >
                  Campaign Objective
                </label>
                <input
                  type="text"
                  id="objective"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  placeholder="e.g., Increase brand awareness, Drive sales"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Target Channels
                </label>
                <div className="mt-1 flex gap-2">
                  <input
                    type="text"
                    value={channelInput}
                    onChange={(e) => setChannelInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddChannel();
                      }
                    }}
                    className="block flex-1 rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                    placeholder="e.g., social, email, blog"
                  />
                  <button
                    type="button"
                    onClick={handleAddChannel}
                    className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
                  >
                    Add
                  </button>
                </div>
                {channels.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {channels.map((channel) => (
                      <span
                        key={channel}
                        className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800"
                      >
                        {channel}
                        <button
                          type="button"
                          onClick={() => handleRemoveChannel(channel)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={generating}
                  className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {generating ? "Generating..." : "Generate Content"}
                </button>
                <button
                  type="button"
                  onClick={() => router.push(`/projects/${id}`)}
                  className="rounded-md bg-gray-200 px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        ) : polling && !response ? (
          /* Polling/Loading State */
          <div className="rounded-lg bg-white p-6 shadow">
            <div className="flex flex-col items-center justify-center py-12">
              <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
              <h3 className="mb-2 text-xl font-semibold text-gray-900">
                Generating Content...
              </h3>
              <p className="text-sm text-gray-600">
                {generationStatus === "pending" && "Request accepted, starting generation..."}
                {generationStatus === "processing" && "Content is being generated, please wait..."}
                {generationStatus === null && "Initializing generation..."}
              </p>
              {generationId && (
                <p className="mt-2 text-xs text-gray-500">
                  Generation ID: {generationId}
                </p>
              )}
            </div>
          </div>
        ) : response ? (
          /* Generated Content Display */
          <div className="space-y-6">
            <div className="flex items-center justify-between rounded-lg bg-white p-6 shadow">
              <h3 className="text-2xl font-bold text-gray-900">
                Generated Content
              </h3>
              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setResponse(null);
                    setPolling(false);
                    setGenerationStatus(null);
                    setGenerationId(null);
                    setBrief("");
                    setBrandTone("");
                    setAudience("");
                    setObjective("");
                    setChannels([]);
                    if (pollingIntervalRef.current) {
                      clearInterval(pollingIntervalRef.current);
                      pollingIntervalRef.current = null;
                    }
                  }}
                  className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
                >
                  Generate New
                </button>
                <button
                  onClick={() => router.push(`/projects/${id}`)}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Back to Project
                </button>
              </div>
            </div>

            <div className="rounded-lg bg-white p-6 shadow">
              <ContentVariants
                response={response}
                onEdit={handleEditVariant}
                isUpdating={updating}
              />
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

