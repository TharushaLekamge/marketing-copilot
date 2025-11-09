"use client";

import { GenerationResponse } from "@/lib/api";
import { useState } from "react";

interface ContentVariantsProps {
  response: GenerationResponse;
  onEdit?: (variantType: string, content: string) => void | Promise<void>;
  isUpdating?: boolean;
}

export default function ContentVariants({
  response,
  onEdit,
  isUpdating = false,
}: ContentVariantsProps) {
  const [editing, setEditing] = useState<{
    variantType: string;
    content: string;
  } | null>(null);

  const handleEdit = (variantType: string, content: string) => {
    setEditing({ variantType, content });
  };

  const handleSave = async () => {
    if (editing && onEdit) {
      await onEdit(editing.variantType, editing.content);
    }
    setEditing(null);
  };

  const handleCancel = () => {
    setEditing(null);
  };

  const getVariantTitle = (variantType: string): string => {
    switch (variantType) {
      case "short_form":
        return "Short Form";
      case "long_form":
        return "Long Form";
      case "cta":
        return "Call to Action";
      default:
        return variantType;
    }
  };

  const getVariantIcon = (variantType: string): string => {
    switch (variantType) {
      case "short_form":
        return "📱";
      case "long_form":
        return "📄";
      case "cta":
        return "🎯";
      default:
        return "📝";
    }
  };

  const variants = [
    {
      type: "short_form",
      content: response.short_form,
      title: getVariantTitle("short_form"),
      icon: getVariantIcon("short_form"),
    },
    {
      type: "long_form",
      content: response.long_form,
      title: getVariantTitle("long_form"),
      icon: getVariantIcon("long_form"),
    },
    {
      type: "cta",
      content: response.cta,
      title: getVariantTitle("cta"),
      icon: getVariantIcon("cta"),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-bold text-gray-900">Generated Content</h3>
        {response.metadata && (
          <div className="text-sm text-gray-500">
            <span className="font-medium">Model:</span> {response.metadata.model}
            {response.metadata.tokens_used && (
              <>
                {" "}
                | <span className="font-medium">Tokens:</span>{" "}
                {response.metadata.tokens_used}
              </>
            )}
            {response.metadata.generation_time && (
              <>
                {" "}
                | <span className="font-medium">Time:</span>{" "}
                {response.metadata.generation_time.toFixed(2)}s
              </>
            )}
          </div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-3">
        {variants.map((variant) => (
          <div
            key={variant.type}
            className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{variant.icon}</span>
                <h4 className="text-lg font-semibold text-gray-900">
                  {variant.title}
                </h4>
              </div>
              {onEdit && (
                <button
                  onClick={() => handleEdit(variant.type, variant.content)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Edit
                </button>
              )}
            </div>

            {editing?.variantType === variant.type ? (
              <div className="space-y-3">
                <textarea
                  value={editing.content}
                  onChange={(e) =>
                    setEditing({ ...editing, content: e.target.value })
                  }
                  className="w-full rounded-md border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  rows={8}
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={isUpdating}
                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isUpdating ? "Saving..." : "Save"}
                  </button>
                  <button
                    onClick={handleCancel}
                    className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="whitespace-pre-wrap text-sm text-gray-700">
                  {variant.content}
                </p>
                {response.variants && (
                  <div className="mt-4 flex gap-4 text-xs text-gray-500">
                    <span>
                      {response.variants.find((v) => v.variant_type === variant.type)
                        ?.character_count || 0}{" "}
                      chars
                    </span>
                    <span>
                      {response.variants.find((v) => v.variant_type === variant.type)
                        ?.word_count || 0}{" "}
                      words
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

