"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ExecutionResponse } from "@/lib/types";
import { StatusIcon } from "@/components/icons";
import { format } from "date-fns";

export default function ExecutionsPage() {
  const { data: executions, isLoading, error } = useQuery<ExecutionResponse[]>({
    queryKey: ["executions"],
    queryFn: () => api.get<ExecutionResponse[]>("/executions?limit=50"),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight">Executions</h2>
          <p className="text-sm text-foreground-muted mt-1">Global execution history across all workflows.</p>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-red-500/5 border border-red-500/20 text-red-500 text-sm">
          Failed to load executions: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-surface border border-border"></div>
          <div className="h-10 bg-surface border border-border"></div>
          <div className="h-10 bg-surface border border-border"></div>
        </div>
      ) : executions?.length === 0 ? (
        <div className="border border-border bg-surface p-12 text-center text-foreground-muted">
          No executions found.
        </div>
      ) : (
        <div className="border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-background">
              <tr>
                <th className="px-4 py-3 font-medium text-foreground-muted w-12"></th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Execution ID</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Workflow ID</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {executions?.map((ex) => (
                <tr key={ex.id} className="hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-3">
                    <StatusIcon status={ex.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link href={`/executions/${ex.id}`} className="hover:text-brand transition-colors">
                      {ex.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground-muted">
                    <Link href={`/workflows/${ex.workflow_id}`} className="hover:text-brand transition-colors">
                      {ex.workflow_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium px-2 py-1 bg-background border border-border">
                      {ex.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
