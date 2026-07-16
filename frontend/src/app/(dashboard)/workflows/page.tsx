"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkflowListResponse } from "@/lib/types";
import { Icons } from "@/components/icons";
import { PageHeader, LinkButton, Table, Th, EmptyState } from "@/components/ui";
import { format } from "date-fns";
import { usePageReveal, useRowStagger } from "@/lib/reveal";

export default function WorkflowsPage() {
  const { data: workflows, isLoading, error } = useQuery<WorkflowListResponse[]>({
    queryKey: ["workflows"],
    queryFn: () => api.get<WorkflowListResponse[]>("/workflows"),
  });

  const root = usePageReveal<HTMLDivElement>();
  const rowsKey = workflows?.map((w) => w.id).join(",");
  const tbodyScope = useRowStagger<HTMLTableSectionElement>(rowsKey, "[data-row]");

  return (
    <div ref={root} className="space-y-8">
      <div data-reveal-head>
        <PageHeader
          title="Workflows"
          description="Author, version, and execute workflow definitions."
          actions={
            <LinkButton href="/workflows/new" variant="primary">
              New Workflow
            </LinkButton>
          }
        />
      </div>

      {error ? (
        <div className="p-4 bg-danger-soft border border-danger-border text-danger text-sm">
          Failed to load workflows: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
        </div>
      ) : workflows?.length === 0 ? (
        <EmptyState
          icon={<Icons.Workflow className="w-10 h-10" />}
          title="No workflows yet"
          description="Create your first workflow definition to start orchestrating distributed jobs."
          action={
            <LinkButton href="/workflows/new" variant="primary">
              Create Workflow
            </LinkButton>
          }
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Description</Th>
              <Th className="w-28">Version</Th>
              <Th className="w-48">Updated</Th>
              <Th className="w-12" />
            </tr>
          </thead>
          <tbody ref={tbodyScope} className="divide-y divide-border">
            {workflows?.map((wf) => (
              <tr key={wf.id} data-row className="hover:bg-surface-hover transition-colors group">
                <td className="px-4 py-3">
                  <Link
                    href={`/workflows/${wf.id}`}
                    className="font-medium hover:underline underline-offset-2"
                  >
                    {wf.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-foreground-muted truncate max-w-[300px]">
                  {wf.description || "—"}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-foreground-muted">
                  v{wf.latest_version_number}
                </td>
                <td className="px-4 py-3 text-foreground-muted text-xs font-mono">
                  {format(new Date(wf.updated_at), "MMM d, yyyy · HH:mm")}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/workflows/${wf.id}`}
                    className="text-foreground-faint hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity inline-block"
                  >
                    <Icons.ChevronRight className="w-4 h-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
