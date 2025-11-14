"use client";

import { useAuth } from "@/contexts/AuthContext";
import { apiClient, Asset, GenerationResponse, Project } from "@/lib/api";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [generationRecords, setGenerationRecords] = useState<GenerationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const pollingIntervalsRef = React.useRef<Record<string, NodeJS.Timeout>>({});

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

  const loadAssets = useCallback(async () => {
    try {
      const data = await apiClient.getAssets(id);
      setAssets(data);
    } catch (err) {
      console.error("Failed to load assets:", err);
    }
  }, [id]);

  const loadGenerationRecords = useCallback(async () => {
    try {
      const data = await apiClient.getGenerationRecords(id);
      setGenerationRecords(data);
    } catch (err) {
      console.error("Failed to load generation records:", err);
    }
  }, [id]);

  useEffect(() => {
    if (user && id) {
      Promise.all([loadProject(), loadAssets(), loadGenerationRecords()]);
    }
  }, [user, id, loadProject, loadAssets, loadGenerationRecords]);

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      // Access current ref value in cleanup to get all intervals
      const intervals = pollingIntervalsRef.current;
      Object.values(intervals).forEach((interval) => {
        clearInterval(interval);
      });
    };
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      setError(null);
      await apiClient.uploadAsset(id, file);
      await loadAssets();
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    if (!confirm("Are you sure you want to delete this asset?")) {
      return;
    }

    try {
      await apiClient.deleteAsset(id, assetId);
      await loadAssets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete asset");
    }
  };

  const handleDownloadAsset = async (asset: Asset) => {
    try {
      const blob = await apiClient.downloadAsset(id, asset.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = asset.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download file");
    }
  };

  const handleIngestAsset = async (assetId: string) => {
    try {
      setIngesting((prev) => ({ ...prev, [assetId]: true }));
      setError(null);
      await apiClient.ingestAsset(id, assetId);
      // Reload assets to get updated status
      await loadAssets();
      // Start polling to check ingestion status
      let pollCount = 0;
      const maxPolls = 150; // 5 minutes at 2 second intervals
      const pollInterval = setInterval(async () => {
        pollCount++;
        const updatedAssets = await apiClient.getAssets(id);
        setAssets(updatedAssets);
        
        const updatedAsset = updatedAssets.find((a) => a.id === assetId);
        if (updatedAsset && !updatedAsset.ingesting && updatedAsset.ingested) {
          clearInterval(pollInterval);
          delete pollingIntervalsRef.current[assetId];
          setIngesting((prev) => {
            const newState = { ...prev };
            delete newState[assetId];
            return newState;
          });
        }
        // Stop polling after max attempts
        if (pollCount >= maxPolls) {
          clearInterval(pollInterval);
          delete pollingIntervalsRef.current[assetId];
          setIngesting((prev) => {
            const newState = { ...prev };
            delete newState[assetId];
            return newState;
          });
        }
      }, 2000); // Poll every 2 seconds
      pollingIntervalsRef.current[assetId] = pollInterval;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start ingestion");
      setIngesting((prev) => {
        const newState = { ...prev };
        delete newState[assetId];
        return newState;
      });
    }
  };

  const getFileIcon = (contentType: string): string => {
    if (contentType.startsWith("image/")) return "🖼️";
    if (contentType.includes("pdf")) return "📄";
    if (contentType.includes("word") || contentType.includes("document")) return "📝";
    if (contentType.includes("spreadsheet") || contentType.includes("excel")) return "📊";
    if (contentType.includes("presentation") || contentType.includes("powerpoint")) return "📊";
    return "📎";
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
                onClick={() => router.push("/projects")}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                ← Back to Projects
              </button>
              <h1 className="text-2xl font-bold text-gray-900">
                Marketing Copilot
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.email}</span>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                API Docs
              </a>
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
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-gray-900">{project.name}</h2>
              {project.description && (
                <p className="mt-2 text-lg text-gray-600">{project.description}</p>
              )}
              <p className="mt-4 text-sm text-gray-500">
                Created: {new Date(project.created_at).toLocaleDateString()} | 
                Updated: {new Date(project.updated_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => router.push(`/projects/${id}/assistant`)}
                className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
              >
                🤖 Ask Assistant
              </button>
              <button
                onClick={() => router.push(`/projects/${id}/generate`)}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Generate Content
              </button>
              <button
                onClick={() => router.push(`/projects/${id}/edit`)}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Edit Project
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Assets Section */}
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="text-2xl font-bold text-gray-900">Assets</h3>
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className={`cursor-pointer rounded-md px-4 py-2 text-sm font-medium text-white ${
                  uploading
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                {uploading ? "Uploading..." : "Upload File"}
              </label>
            </div>
          </div>

          {assets.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <p className="text-lg text-gray-600">
                No assets yet. Upload your first file to get started!
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      File
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Uploaded
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {assets.map((asset) => (
                    <tr key={asset.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-4">
                        <div className="flex items-center">
                          <span className="mr-2 text-xl">
                            {getFileIcon(asset.content_type)}
                          </span>
                          <span className="text-sm font-medium text-gray-900">
                            {asset.filename}
                          </span>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                        {asset.content_type}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                            asset.ingested
                              ? "bg-green-100 text-green-800"
                              : asset.ingesting || ingesting[asset.id]
                              ? "bg-blue-100 text-blue-800"
                              : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {asset.ingested
                            ? "Ingested"
                            : asset.ingesting || ingesting[asset.id]
                            ? "Ingesting..."
                            : "Pending"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                        {new Date(asset.created_at).toLocaleDateString()}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleIngestAsset(asset.id)}
                            disabled={asset.ingested || asset.ingesting || ingesting[asset.id]}
                            className="text-green-600 hover:text-green-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                          >
                            Ingest
                          </button>
                          <button
                            onClick={() => handleDownloadAsset(asset)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Download
                          </button>
                          <button
                            onClick={() => handleDeleteAsset(asset.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Generation Records Section */}
        <div className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="text-2xl font-bold text-gray-900">Generation Records</h3>
          </div>

          {generationRecords.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <p className="text-lg text-gray-600">
                No generation records yet. Generate your first content to get started!
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Model
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Short Form Preview
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Tokens
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {generationRecords.map((record) => (
                    <tr key={record.generation_id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                        {record.metadata.model}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        <div className="max-w-md truncate">
                          {record.short_form || "N/A"}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                        {record.metadata.tokens_used || "N/A"}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                        <button
                          onClick={() => router.push(`/projects/${id}/generations/${record.generation_id}`)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

