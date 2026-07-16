"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ExecutionResponse } from "@/lib/types";
import { StatusIcon } from "@/components/icons";
import { PageHeader, Table, Th, EmptyState, Badge } from "@/components/ui";

export default function ExecutionsPage() {
  const { data: executions, isLoading, error } = useQuery<ExecutionResponse[]>({
    queryKey: ["executions"],
    queryFn: () => api.get<ExecutionResponse[]>("/executions?limit=50"),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Executions"
        description="Global execution history across all workflows. Updates live."
      />

      {error ? (
        <div className="p-4 bg-danger-soft border border-danger-border text-danger text-sm">
          Failed to load executions: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
        </div>
      ) : executions?.length === 0 ? (
        <EmptyState
          title="No executions found"
          description="Run a workflow to see its execution history appear here."
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th className="w-12" />
              <Th>Execution ID</Th>
              <Th>Workflow</Th>
              <Th className="w-40">Status</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {executions?.map((ex) => (
              <tr key={ex.id} className="hover:bg-surface-hover transition-colors">
                <td className="px-4 py-3">
                  <StatusIcon status={ex.status} />
                </td>
                <td className="px-4 py-3 font-mono text-xs">
                  <Link
                    href={`/executions/${ex.id}`}
                    className="hover:underline underline-offset-2"
                  >
                    {ex.id}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-foreground-muted">
                  <Link
                    href={`/workflows/${ex.workflow_id}`}
                    className="hover:underline underline-offset-2"
                  >
                    {ex.workflow_id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Badge danger={["FAILED", "DEAD_LETTERED", "PARTIAL_FAILED"].includes(ex.status)}>
                    {ex.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
