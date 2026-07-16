"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DeadLetterJobResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-red-500">Dead Letter Queue</h2>
          <p className="text-sm text-foreground-muted mt-1">Failed execution nodes requiring manual intervention.</p>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-red-500/5 border border-red-500/20 text-red-500 text-sm">
          Failed to load DLQ: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-surface border border-border"></div>
          <div className="h-10 bg-surface border border-border"></div>
        </div>
      ) : dlq?.length === 0 ? (
        <div className="border border-border bg-surface p-12 text-center text-foreground-muted flex flex-col items-center">
          <Icons.Archive className="w-10 h-10 opacity-20 mb-4" />
          The Dead Letter Queue is currently empty.
        </div>
      ) : (
        <div className="border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-background">
              <tr>
                <th className="px-4 py-3 font-medium text-foreground-muted w-12"></th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Execution</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Reason</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Attempts</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Timestamp</th>
                <th className="px-4 py-3 font-medium text-foreground-muted text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {dlq?.map((job) => (
                <React.Fragment key={job.id}>
                  <tr className="hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-3">
                      <StatusIcon status={job.resolved_at ? "COMPLETED" : "DEAD_LETTERED"} className={job.resolved_at ? "" : "!text-red-500"} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link href={`/executions/${job.execution_id}`} className="hover:text-brand transition-colors">
                        {job.execution_id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground-muted max-w-[200px] truncate">
                      {job.reason}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {job.attempts}
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground-muted">
                      {format(new Date(job.created_at), "MMM d, HH:mm")}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!job.resolved_at ? (
                        <button
                          onClick={() => setSelectedJob(job.id === selectedJob ? null : job.id)}
                          className="px-3 py-1 bg-surface border border-border text-xs font-medium hover:bg-surface-hover transition-colors"
                        >
                          Resolve
                        </button>
                      ) : (
                        <span className="text-xs text-foreground-muted">Resolved</span>
                      )}
                    </td>
                  </tr>
                  {selectedJob === job.id && !job.resolved_at && (
                    <tr>
                      <td colSpan={6} className="bg-background px-4 py-4 border-b border-border">
                        <div className="flex gap-4 items-start max-w-2xl">
                          <input
                            type="text"
                            value={resolveNote}
                            onChange={(e) => setResolveNote(e.target.value)}
                            placeholder="Resolution note (e.g. Fixed upstream API issue)"
                            className="flex-1 bg-surface border border-border px-3 py-2 text-sm focus:outline-none focus:border-brand"
                            autoFocus
                          />
                          <button
                            onClick={() => resolveMutation.mutate({ id: job.id, note: resolveNote })}
                            disabled={resolveMutation.isPending || !resolveNote}
                            className="bg-brand hover:bg-brand-hover text-white px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors shrink-0"
                          >
                            {resolveMutation.isPending ? "Resolving..." : "Confirm Resolve"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
