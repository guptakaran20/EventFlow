"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkerResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { formatDistanceToNow } from "date-fns";

export default function WorkersPage() {
  const { data: workers, isLoading, error } = useQuery<WorkerResponse[]>({
    queryKey: ["workers"],
    queryFn: () => api.get<WorkerResponse[]>("/workers"),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight">Workers</h2>
          <p className="text-sm text-foreground-muted mt-1">Active instances executing workflow nodes.</p>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-red-500/5 border border-red-500/20 text-red-500 text-sm">
          Failed to load workers: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-10 bg-surface border border-border"></div>
          <div className="h-10 bg-surface border border-border"></div>
        </div>
      ) : workers?.length === 0 ? (
        <div className="border border-border bg-surface p-12 text-center text-foreground-muted">
          <Icons.Server className="w-10 h-10 mx-auto opacity-20 mb-4" />
          No active workers connected.
        </div>
      ) : (
        <div className="border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-background">
              <tr>
                <th className="px-4 py-3 font-medium text-foreground-muted">Hostname</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">PID</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Status</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Last Heartbeat</th>
                <th className="px-4 py-3 font-medium text-foreground-muted">Current Job</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {workers?.map((worker) => {
                const lastHeartbeat = new Date(worker.last_heartbeat);
                const isStale = (Date.now() - lastHeartbeat.getTime()) > 30000;

                return (
                  <tr key={worker.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-3 font-mono text-xs">{worker.hostname}</td>
                    <td className="px-4 py-3 font-mono text-xs text-foreground-muted">{worker.pid}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {worker.status === "IDLE" && !isStale && (
                          <StatusIcon status="COMPLETED" className="w-4 h-4 !text-foreground-muted" />
                        )}
                        {worker.status === "BUSY" && !isStale && (
                          <StatusIcon status="RUNNING" className="w-4 h-4" />
                        )}
                        {isStale && (
                          <StatusIcon status="FAILED" className="w-4 h-4 !text-red-500" />
                        )}
                        <span className="text-xs">{isStale ? "STALE" : worker.status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground-muted">
                      {formatDistanceToNow(lastHeartbeat, { addSuffix: true })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-brand truncate max-w-[200px]">
                      {worker.current_node_id || "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
