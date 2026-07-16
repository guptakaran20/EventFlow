"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ExecutionResponse, ExecutionLogResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { useExecutionWebSocket } from "@/lib/websocket";
import { format } from "date-fns";

export default function ExecutionDetailPage() {
  const params = useParams();
  const executionId = params.id as string;
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

  if (error) {
    return <div className="p-4 bg-red-500/5 text-red-500 border border-red-500/20 text-sm">Failed to load execution.</div>;
  }

  if (isLoading || !execution) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-medium tracking-tight flex items-center gap-3">
            Execution
            <StatusIcon status={execution.status} className="w-5 h-5" />
          </h2>
          <div className="text-sm text-foreground-muted mt-1 font-mono">
            ID: {execution.id}
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono px-3 py-1 bg-surface border border-border">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          {isConnected ? 'WS Connected' : 'WS Disconnected'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden">
        {/* Left Column: Flow representation (Table for MVP) */}
        <div className="lg:col-span-2 border border-border bg-surface flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-background flex justify-between items-center">
            <span className="text-sm font-medium">Nodes</span>
          </div>
          <div className="overflow-auto flex-1 p-4">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th className="pb-3 font-medium text-foreground-muted">Node</th>
                  <th className="pb-3 font-medium text-foreground-muted">Type</th>
                  <th className="pb-3 font-medium text-foreground-muted">Attempt</th>
                  <th className="pb-3 font-medium text-foreground-muted">Status</th>
                  <th className="pb-3 font-medium text-foreground-muted text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {execution.node_executions.map(node => (
                  <tr key={node.id} className="group">
                    <td className="py-3 font-medium">{node.node_id}</td>
                    <td className="py-3 font-mono text-xs text-foreground-muted">{node.node_type}</td>
                    <td className="py-3 text-foreground-muted text-xs">{node.attempt} / {node.max_attempts}</td>
                    <td className="py-3 flex items-center gap-2">
                      <StatusIcon status={node.status} />
                      <span className="text-xs">{node.status}</span>
                    </td>
                    <td className="py-3 text-right">
                      {node.status === "DEAD_LETTERED" && (
                        <button
                          onClick={() => retryMutation.mutate(node.node_id)}
                          disabled={retryMutation.isPending}
                          className="px-2 py-1 bg-brand/10 text-brand text-xs font-medium hover:bg-brand/20 transition-colors"
                        >
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {execution.node_executions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-foreground-muted text-xs">
                      No nodes executed yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Logs */}
        <div className="border border-border bg-surface flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-background flex justify-between items-center">
            <span className="text-sm font-medium">Execution Logs</span>
          </div>
          <div className="flex-1 overflow-auto bg-black text-gray-300 p-4 font-mono text-xs leading-relaxed space-y-1">
            {logs?.map(log => (
              <div key={log.log_id} className="flex gap-3">
                <span className="text-gray-500 shrink-0">
                  {format(new Date(log.timestamp), "HH:mm:ss.SSS")}
                </span>
                <span className={`shrink-0 w-12 ${
                  log.level === 'ERROR' ? 'text-red-400' :
                  log.level === 'WARN' ? 'text-yellow-400' :
                  'text-blue-400'
                }`}>
                  [{log.level}]
                </span>
                <span className="break-all">{log.message}</span>
              </div>
            ))}
            {!logs?.length && (
              <div className="text-gray-600 italic">Waiting for logs...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
