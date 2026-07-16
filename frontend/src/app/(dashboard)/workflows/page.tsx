"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkflowListResponse } from "@/lib/types";
import { Icons } from "@/components/icons";
import { format } from "date-fns";

export default function WorkflowsPage() {
  const { data: workflows, isLoading, error } = useQuery<WorkflowListResponse[]>({
    queryKey: ["workflows"],
    queryFn: () => api.get<WorkflowListResponse[]>("/workflows"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight">Workflows</h2>
          <p className="text-sm text-foreground-muted mt-1">Manage and author workflow definitions.</p>
        </div>
        <Link 
          href="/workflows/new" 
          className="bg-brand hover:bg-brand-hover text-white px-4 py-2 text-sm font-medium transition-colors"
        >
          New Workflow
        </Link>
      </div>

      {error ? (
        <div className="p-4 bg-red-500/5 border border-red-500/20 text-red-500 text-sm">
          Failed to load workflows: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-2 bg-border rounded w-3/4"></div>
            <div className="h-2 bg-border rounded w-1/2"></div>
            <div className="h-2 bg-border rounded w-5/6"></div>
          </div>
        </div>
      ) : workflows?.length === 0 ? (
        <div className="border border-border bg-surface p-12 flex flex-col items-center justify-center text-center">
          <Icons.Workflow className="w-12 h-12 text-foreground-muted opacity-20 mb-4" />
          <h3 className="text-lg font-medium text-foreground">No workflows found</h3>
          <p className="text-foreground-muted mt-2 max-w-sm text-sm">
            You haven't created any workflows yet. Get started by creating your first workflow definition.
          </p>
          <Link 
            href="/workflows/new" 
            className="mt-6 bg-surface hover:bg-surface-hover border border-border text-foreground px-4 py-2 text-sm font-medium transition-colors"
          >
            Create Workflow
          </Link>
        </div>
      ) : (
        <div className="border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-background">
              <tr>
                <th className="px-4 py-3 font-medium text-foreground-muted">Name</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Description</th>
                <th className="px-4 py-3 font-medium text-foreground-muted w-32">Version</th>
                <th className="px-4 py-3 font-medium text-foreground-muted w-48">Updated</th>
                <th className="px-4 py-3 font-medium text-foreground-muted w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {workflows?.map((wf) => (
                <tr key={wf.id} className="hover:bg-surface-hover transition-colors group">
                  <td className="px-4 py-3">
                    <Link href={`/workflows/${wf.id}`} className="font-medium hover:text-brand transition-colors">
                      {wf.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-foreground-muted truncate max-w-[300px]">
                    {wf.description || "-"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    v{wf.latest_version_number}
                  </td>
                  <td className="px-4 py-3 text-foreground-muted text-xs">
                    {format(new Date(wf.updated_at), "MMM d, yyyy HH:mm")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/workflows/${wf.id}`} className="text-foreground-muted hover:text-brand opacity-0 group-hover:opacity-100 transition-opacity">
                      <Icons.ChevronRight className="w-4 h-4 inline-block" />
                    </Link>
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
