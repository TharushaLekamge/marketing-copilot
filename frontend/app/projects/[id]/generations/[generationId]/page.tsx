"use client";

import ContentVariants from "@/components/ContentVariants";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiClient,
  GenerationResponse,
  GenerationUpdateRequest,
  Project,
} from "@/lib/api";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";

export default function GenerationRecordPage({
  params,
}: {
  params: Promise<{ id: string; generationId: string }>;
}) {
  const { id, generationId } = React.use(params);
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [generationRecord, setGenerationRecord] = useState<GenerationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const loadProject = useCallback(async () => {
    try {
      const data = await apiClient.getProject(id);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
      if (err instanceof Error && err.message.includes("404")) {
        router.push("/projects");
      }
    }
  }, [id, router]);

  const loadGenerationRecord = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getGenerationRecord(generationId);
      setGenerationRecord(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load generation record");
      if (err instanceof Error && err.message.includes("404")) {
        router.push(`/projects/${id}`);
      }
    } finally {
      setLoading(false);
    }
  }, [generationId, id, router]);

  useEffect(() => {
    if (user && id && generationId) {
      Promise.all([loadProject(), loadGenerationRecord()]);
    }
  }, [user, id, generationId, loadProject, loadGenerationRecord]);

  const handleEdit = async (variantType: string, content: string) => {
    if (!generationRecord) return;

    try {
      setUpdating(true);
      setError(null);
      setSuccessMessage(null);

      const updateRequest: GenerationUpdateRequest = {
        short_form: variantType === "short_form" ? content : generationRecord.short_form,
        long_form: variantType === "long_form" ? content : generationRecord.long_form,
        cta: variantType === "cta" ? content : generationRecord.cta,
      };

      const result = await apiClient.updateGenerationRecord(generationId, updateRequest);
      
      // Update with server response
      setGenerationRecord(result.updated);
      setSuccessMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update content");
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

  if (!user || !project || !generationRecord) {
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
                Generation Record ID: {generationRecord.generation_id}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => router.push(`/projects/${id}/generate`)}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Generate New Content
              </button>
              <button
                onClick={() => router.push(`/projects/${id}`)}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Back to Project
              </button>
            </div>
          </div>
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

        {/* Generation Record Content */}
        <div className="rounded-lg bg-white p-6 shadow">
          <ContentVariants
            response={generationRecord}
            onEdit={handleEdit}
            isUpdating={updating}
          />
        </div>
      </main>
    </div>
  );
}

