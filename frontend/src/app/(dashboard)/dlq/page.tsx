"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DeadLetterJobResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { PageHeader, Table, Th, EmptyState, Button } from "@/components/ui";
import { format } from "date-fns";

export default function DLQPage() {
  const queryClient = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [resolveNote, setResolveNote] = useState("");

  const { data: dlq, isLoading, error } = useQuery<DeadLetterJobResponse[]>({
    queryKey: ["dlq"],
    queryFn: () => api.get<DeadLetterJobResponse[]>("/dlq?limit=50"),
  });

  const resolveMutation = useMutation({
    mutationFn: async ({ id, note }: { id: string; note: string }) => {
      return api.post(`/dlq/${id}/resolve`, { resolution_note: note });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dlq"] });
      setSelectedJob(null);
      setResolveNote("");
    },
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dead Letter Queue"
        description="Execution nodes that exhausted their retries and require manual intervention."
        danger
      />

      {error ? (
        <div className="p-4 bg-danger-soft border border-danger-border text-danger text-sm">
          Failed to load DLQ: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
        </div>
      ) : dlq?.length === 0 ? (
        <EmptyState
          icon={<Icons.Archive className="w-10 h-10" />}
          title="Dead letter queue is empty"
          description="No failed jobs need attention. Every node has completed or recovered."
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th className="w-12" />
              <Th>Execution</Th>
              <Th>Reason</Th>
              <Th className="w-24">Attempts</Th>
              <Th className="w-44">Timestamp</Th>
              <Th className="w-32 text-right">Action</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {dlq?.map((job) => (
              <React.Fragment key={job.id}>
                <tr className="hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-3">
                    <StatusIcon status={job.resolved_at ? "COMPLETED" : "DEAD_LETTERED"} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link
                      href={`/executions/${job.execution_id}`}
                      className="hover:underline underline-offset-2"
                    >
                      {job.execution_id.substring(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground-muted max-w-[240px] truncate">
                    {job.reason}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">{job.attempts}</td>
                  <td className="px-4 py-3 text-xs text-foreground-muted font-mono">
                    {format(new Date(job.created_at), "MMM d · HH:mm")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {!job.resolved_at ? (
                      <Button
                        onClick={() =>
                          setSelectedJob(job.id === selectedJob ? null : job.id)
                        }
                        className="h-7 px-2.5 text-xs"
                      >
                        Resolve
                      </Button>
                    ) : (
                      <span className="text-xs text-foreground-faint">Resolved</span>
                    )}
                  </td>
                </tr>
                {selectedJob === job.id && !job.resolved_at && (
                  <tr>
                    <td colSpan={6} className="bg-surface-2 px-4 py-4 border-b border-border">
                      <div className="flex gap-3 items-center max-w-2xl">
                        <input
                          type="text"
                          value={resolveNote}
                          onChange={(e) => setResolveNote(e.target.value)}
                          placeholder="Resolution note (e.g. Fixed upstream API issue)"
                          className="flex-1 bg-surface border border-border-strong px-3 h-9 text-sm focus:outline-none focus:border-foreground transition-colors"
                          autoFocus
                        />
                        <Button
                          variant="primary"
                          onClick={() =>
                            resolveMutation.mutate({ id: job.id, note: resolveNote })
                          }
                          disabled={resolveMutation.isPending || !resolveNote}
                          className="shrink-0"
                        >
                          {resolveMutation.isPending ? "Resolving…" : "Confirm"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
