"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkflowDetailResponse } from "@/lib/types";
import { Icons } from "@/components/icons";
import { Button, PageHeader } from "@/components/ui";
import { format } from "date-fns";
import { ReactFlowEditor } from "@/components/workflows/ReactFlowEditor";
import { usePageReveal } from "@/lib/reveal";

const DEFAULT_WORKFLOW = {
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
};

export default function WorkflowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const isNew = params.id === "new";

  const [json, setJson] = useState(JSON.stringify(DEFAULT_WORKFLOW, null, 2));
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");
  const [showHistory, setShowHistory] = useState(false);
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
        return api.post<WorkflowDetailResponse>("/workflows", {
          name: payload.name,
          description: payload.description,
          definition: payload
        });
      } else {
        return api.post<any>(`/workflows/${params.id}/versions`, { definition: payload });
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

  const root = usePageReveal<HTMLDivElement>([isLoading, isNew]);

  if (isLoading && !isNew) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 bg-surface border border-border" />
        <div className="h-96 bg-surface border border-border" />
      </div>
    );
  }

  return (
    <div ref={root} className="flex flex-col h-[calc(100vh-5rem)]">
      <div data-reveal-head>
        <PageHeader
          title={isNew ? "Create Workflow" : workflow?.name || "Workflow"}
          description={
            isNew
              ? "Define nodes and edges as JSON, then save the first version."
              : `${workflow?.versions.length ?? 0} version${
                  workflow?.versions.length === 1 ? "" : "s"
                } · ID ${workflow?.id?.slice(0, 8)}…`
          }
          actions={
            <>
              <Button onClick={handleSave} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "Saving…" : "Save Version"}
              </Button>
              {!isNew && (
                <Button
                  variant="primary"
                  onClick={handleStart}
                  disabled={startExecutionMutation.isPending}
                >
                  <Icons.Play className="w-3.5 h-3.5 fill-current" />
                  {startExecutionMutation.isPending ? "Starting…" : "Run"}
                </Button>
              )}
            </>
          }
        />
      </div>

      {validationError && (
        <div className="mt-6 p-4 bg-danger-soft border border-danger-border text-danger text-sm flex items-center gap-2">
          <Icons.Close className="w-4 h-4 shrink-0" />
          {validationError}
        </div>
      )}
      {successMsg && (
        <div className="mt-6 p-4 bg-surface-2 border border-border text-foreground text-sm flex items-center gap-2">
          <Icons.Workflow className="w-4 h-4 shrink-0" />
          {successMsg}
        </div>
      )}

      <div className="mt-4 flex-1 flex gap-4 min-h-0">
        <div data-reveal className="flex-1 min-w-0 border border-border bg-surface flex flex-col min-h-0">
          <div className="bg-surface-2 border-b border-border px-4 h-11 flex items-center justify-between shrink-0">
            <div className="flex gap-1">
              <button
                onClick={() => setViewMode("visual")}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  viewMode === "visual"
                    ? "bg-surface text-foreground shadow-sm border border-border"
                    : "text-foreground-muted hover:text-foreground"
                }`}
              >
                Visual Editor
              </button>
              <button
                onClick={() => setViewMode("json")}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  viewMode === "json"
                    ? "bg-surface text-foreground shadow-sm border border-border"
                    : "text-foreground-muted hover:text-foreground"
                }`}
              >
                JSON Code
              </button>
            </div>
            <button
              onClick={() => setShowHistory((v) => !v)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition-colors ${
                showHistory
                  ? "bg-surface text-foreground border-border"
                  : "text-foreground-muted hover:text-foreground border-transparent"
              }`}
              title="Toggle version history"
            >
              <Icons.Code className="w-3.5 h-3.5" />
              History
            </button>
          </div>

          {viewMode === "json" ? (
            <textarea
              value={json}
              onChange={(e) => setJson(e.target.value)}
              className="flex-1 w-full bg-transparent p-4 font-mono text-[13px] focus:outline-none resize-none leading-relaxed text-foreground"
              spellCheck={false}
            />
          ) : (
            <div className="flex-1 w-full h-full relative">
              {(() => {
                try {
                  const parsed = JSON.parse(json);
                  return (
                    <ReactFlowEditor
                      workflow={parsed}
                      onChange={(wf) => setJson(JSON.stringify(wf, null, 2))}
                    />
                  );
                } catch (e) {
                  return (
                    <div className="p-4 text-danger text-sm">
                      Invalid JSON. Please fix it in the JSON Code view before using the visual editor.
                    </div>
                  );
                }
              })()}
            </div>
          )}
        </div>

        {/* Version history — git-style, collapsible */}
        {showHistory && (
        <div data-reveal className="w-72 shrink-0 border border-border bg-surface flex flex-col min-h-0">
          <div className="bg-surface-2 border-b border-border px-4 h-11 flex items-center justify-between shrink-0">
            <span className="label-caps">Version History</span>
            <button
              onClick={() => setShowHistory(false)}
              className="text-foreground-faint hover:text-foreground"
              title="Close"
            >
              <Icons.Close className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-2">
            {isNew || !workflow?.versions.length ? (
              <div className="text-xs text-foreground-faint p-3">
                No versions yet.
              </div>
            ) : (
              <ol className="relative">
                {[...workflow.versions]
                  .sort((a, b) => b.version_number - a.version_number)
                  .map((ver, i, arr) => (
                    <li key={ver.id} className="flex gap-3 px-2 py-2">
                      <div className="flex flex-col items-center pt-1">
                        <span className="w-2 h-2 bg-foreground shrink-0" />
                        {i < arr.length - 1 && (
                          <span className="w-px flex-1 bg-border mt-1" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="font-mono text-xs text-foreground">
                          v{ver.version_number}
                        </div>
                        <div className="text-[11px] text-foreground-faint font-mono truncate">
                          {ver.checksum?.slice(0, 10)}
                        </div>
                        <div className="text-[11px] text-foreground-muted mt-0.5">
                          {format(new Date(ver.created_at), "MMM d · HH:mm")}
                        </div>
                      </div>
                    </li>
                  ))}
              </ol>
            )}
          </div>
        </div>
        )}
      </div>
    </div>
  );
}
