"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ExecutionResponse, ExecutionLogResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { useExecutionWebSocket } from "@/lib/websocket";
import { Button, Badge } from "@/components/ui";
import { format } from "date-fns";
import { usePageReveal, useRowStagger } from "@/lib/reveal";
import { toast } from "sonner";

export default function ExecutionDetailPage() {
  const params = useParams();
  const executionId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  // Wire up WebSocket for live updates
  const { isConnected } = useExecutionWebSocket(executionId);

  const { data: execution, isLoading, error } = useQuery<ExecutionResponse>({
    queryKey: ["execution", executionId],
    queryFn: () => api.get<ExecutionResponse>(`/executions/${executionId}`),
  });

  const { data: logs } = useQuery<ExecutionLogResponse[]>({
    queryKey: ["execution_logs", executionId],
    queryFn: () => api.get<ExecutionLogResponse[]>(`/executions/${executionId}/logs`),
    enabled: !!execution,
  });

  const retryMutation = useMutation({
    mutationFn: async (nodeId: string) => {
      return api.post(`/executions/${executionId}/nodes/${nodeId}/retry`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["execution", executionId] });
      queryClient.invalidateQueries({ queryKey: ["execution_logs", executionId] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      return api.delete(`/executions/${executionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["executions"] });
      router.push("/executions");
    }
  });

  const root = usePageReveal<HTMLDivElement>([execution?.id]);
  const nodesKey = execution?.node_executions
    .map((n) => `${n.id}:${n.status}`)
    .join(",");
  const nodesScope = useRowStagger<HTMLTableSectionElement>(nodesKey, "[data-row]");

  if (error) {
    return <div className="p-4 bg-danger-soft text-danger border border-danger-border text-sm">Failed to load execution.</div>;
  }

  if (isLoading || !execution) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-56 bg-surface border border-border" />
        <div className="h-96 bg-surface border border-border" />
      </div>
    );
  }

  return (
    <div ref={root} className="flex flex-col h-[calc(100vh-9rem)]">
      <div data-reveal-head className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <div className="label-caps mb-2 flex items-center gap-2">
            <StatusIcon status={execution.status} className="w-3.5 h-3.5" />
            {execution.status}
          </div>
          <h1 className="font-serif text-3xl md:text-4xl tracking-tight leading-none">
            Execution
          </h1>
          <div className="text-xs text-foreground-muted mt-2 font-mono">
            {execution.id}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-[11px] font-mono px-3 h-8 bg-surface border border-border">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? "bg-foreground animate-pulse" : "bg-danger"
              }`}
            />
            {isConnected ? "Live" : "Disconnected"}
          </div>
          <Button 
            variant="danger" 
            onClick={() => {
              toast("Are you sure you want to delete this execution?", {
                action: {
                  label: "Delete",
                  onClick: () => deleteMutation.mutate(),
                },
                cancel: {
                  label: "Cancel",
                  onClick: () => {},
                },
              });
            }}
            disabled={deleteMutation.isPending}
            className="h-8 text-xs"
          >
            Delete Execution
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden min-h-0">
        {/* Nodes */}
        <div data-reveal className="lg:col-span-2 border border-border bg-surface flex flex-col overflow-hidden min-h-0">
          <div className="px-4 h-11 border-b border-border bg-surface-2 flex justify-between items-center shrink-0">
            <span className="label-caps">Node Executions</span>
            <span className="font-mono text-xs text-foreground-faint">
              {execution.node_executions.length} nodes
            </span>
          </div>
          <div className="overflow-auto flex-1">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-surface-2">
                <tr className="border-b border-border">
                  <th className="px-4 h-10 font-medium text-[11px] uppercase tracking-wider text-foreground-faint">Node</th>
                  <th className="px-4 h-10 font-medium text-[11px] uppercase tracking-wider text-foreground-faint">Type</th>
                  <th className="px-4 h-10 font-medium text-[11px] uppercase tracking-wider text-foreground-faint">Attempt</th>
                  <th className="px-4 h-10 font-medium text-[11px] uppercase tracking-wider text-foreground-faint">Status</th>
                  <th className="px-4 h-10 text-right font-medium text-[11px] uppercase tracking-wider text-foreground-faint">Action</th>
                </tr>
              </thead>
              <tbody ref={nodesScope} className="divide-y divide-border">
                {execution.node_executions.map((node) => (
                  <tr key={node.id} data-row className="group hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-3 font-medium">{node.node_id}</td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground-muted">{node.node_type}</td>
                    <td className="px-4 py-3 text-foreground-muted text-xs font-mono">
                      {node.attempt} / {node.max_attempts}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatusIcon status={node.status} />
                        <span className="text-xs">{node.status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {node.status === "DEAD_LETTERED" && (
                        <Button
                          variant="danger"
                          onClick={() => retryMutation.mutate(node.node_id)}
                          disabled={retryMutation.isPending}
                          className="h-7 px-2.5 text-xs"
                        >
                          Retry
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {execution.node_executions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-foreground-faint text-xs">
                      No nodes executed yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Logs */}
        <div data-reveal className="border border-border bg-surface flex flex-col overflow-hidden min-h-0">
          <div className="px-4 h-11 border-b border-border bg-surface-2 flex justify-between items-center shrink-0">
            <span className="label-caps">Execution Logs</span>
          </div>
          <div className="flex-1 overflow-auto bg-background p-4 font-mono text-[11px] leading-relaxed space-y-1">
            {logs?.map((log) => (
              <div key={log.log_id} className="flex gap-3">
                <span className="text-foreground-faint shrink-0">
                  {format(new Date(log.timestamp), "HH:mm:ss.SSS")}
                </span>
                <span
                  className={`shrink-0 w-14 ${
                    log.level === "ERROR"
                      ? "text-danger"
                      : "text-foreground-muted"
                  }`}
                >
                  [{log.level}]
                </span>
                <span className="break-all text-foreground">{log.message}</span>
              </div>
            ))}
            {!logs?.length && (
              <div className="text-foreground-faint italic">Waiting for logs…</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
