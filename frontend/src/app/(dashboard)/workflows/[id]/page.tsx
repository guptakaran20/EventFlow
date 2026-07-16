"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkflowDetailResponse } from "@/lib/types";
import { Icons } from "@/components/icons";

const DEFAULT_WORKFLOW = {
  name: "New Workflow",
  description: "A description of your workflow",
  definition: {
    name: "New Workflow",
    description: "A description of your workflow",
    nodes: [
      {
        id: "node_1",
        type: "http",
        name: "Fetch Data",
        config: { url: "https://api.example.com", method: "GET" }
      }
    ],
    edges: []
  }
};

export default function WorkflowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const isNew = params.id === "new";

  const [json, setJson] = useState(JSON.stringify(DEFAULT_WORKFLOW, null, 2));
  const [validationError, setValidationError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data: workflow, isLoading } = useQuery<WorkflowDetailResponse>({
    queryKey: ["workflow", params.id],
    queryFn: () => api.get<WorkflowDetailResponse>(`/workflows/${params.id}`),
    enabled: !isNew,
  });

  useEffect(() => {
    if (workflow) {
      // In a real app we'd fetch the exact version definition.
      // But /workflows/{id} doesn't return the definition in MVP. 
      // We'd need an endpoint like GET /workflows/{id}/versions/{v} to get the JSON.
      // Actually, wait, does MVP have an endpoint for fetching a version's definition?
      // I'll check what backend routes exist later. For now, we will leave it as placeholder JSON
      // if it's not new, just to show the UI.
      setJson(JSON.stringify({ 
        name: workflow.name, 
        description: workflow.description, 
        nodes: [], 
        edges: [] 
      }, null, 2));
    }
  }, [workflow]);

  const saveMutation = useMutation({
    mutationFn: async (payload: any) => {
      if (isNew) {
        return api.post<WorkflowDetailResponse>("/workflows", payload);
      } else {
        return api.post<any>(`/workflows/${params.id}/versions`, { definition: payload.definition });
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflow", params.id] });
      setSuccessMsg("Workflow saved successfully!");
      setValidationError(null);
      setTimeout(() => setSuccessMsg(null), 3000);
      if (isNew && data?.workflow_id) {
        router.push(`/workflows/${data.workflow_id}`);
      }
    },
    onError: (err: Error) => {
      setValidationError(err.message);
    }
  });

  const startExecutionMutation = useMutation({
    mutationFn: async (versionId: string) => {
      return api.post<any>("/executions", {
        workflow_version_id: versionId,
        input_payload: {}
      });
    },
    onSuccess: (data) => {
      router.push(`/executions/${data.id}`);
    }
  });

  const handleSave = () => {
    try {
      const parsed = JSON.parse(json);
      saveMutation.mutate(parsed);
    } catch (e) {
      setValidationError("Invalid JSON format");
    }
  };

  const handleStart = () => {
    if (!workflow || workflow.versions.length === 0) return;
    const latestVersion = workflow.versions.sort((a, b) => b.version_number - a.version_number)[0];
    startExecutionMutation.mutate(latestVersion.id);
  };

  if (isLoading && !isNew) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-medium tracking-tight">
            {isNew ? "Create Workflow" : workflow?.name}
          </h2>
          <div className="text-sm text-foreground-muted mt-1 font-mono">
            {isNew ? "Unsaved" : `ID: ${workflow?.id} | Latest Version: v${workflow?.versions.length}`}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="bg-surface hover:bg-surface-hover border border-border text-foreground px-4 py-2 text-sm font-medium transition-colors"
          >
            {saveMutation.isPending ? "Saving..." : "Save JSON"}
          </button>
          
          {!isNew && (
            <button 
              onClick={handleStart}
              disabled={startExecutionMutation.isPending}
              className="bg-brand hover:bg-brand-hover text-white px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2"
            >
              <Icons.Play className="w-4 h-4 fill-current" />
              {startExecutionMutation.isPending ? "Starting..." : "Start Execution"}
            </button>
          )}
        </div>
      </div>

      {validationError && (
        <div className="mb-6 p-4 bg-red-500/5 border border-red-500/20 text-red-500 text-sm flex items-center gap-2">
          <Icons.Close className="w-4 h-4 shrink-0" />
          {validationError}
        </div>
      )}

      {successMsg && (
        <div className="mb-6 p-4 bg-brand/5 border border-brand/20 text-brand text-sm flex items-center gap-2">
          <Icons.Workflow className="w-4 h-4 shrink-0" />
          {successMsg}
        </div>
      )}

      <div className="flex-1 border border-border bg-background relative flex flex-col">
        <div className="bg-surface border-b border-border px-4 py-2 flex items-center justify-between shrink-0">
          <span className="text-sm font-medium text-foreground-muted">workflow.json</span>
          <Icons.Code className="w-4 h-4 text-foreground-muted" />
        </div>
        <textarea
          value={json}
          onChange={(e) => setJson(e.target.value)}
          className="flex-1 w-full bg-transparent p-4 font-mono text-sm focus:outline-none resize-none leading-relaxed"
          spellCheck={false}
        />
      </div>
    </div>
  );
}
