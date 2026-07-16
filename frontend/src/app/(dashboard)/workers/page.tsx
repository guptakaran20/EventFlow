"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkerResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { PageHeader, Table, Th, EmptyState } from "@/components/ui";
import { formatDistanceToNow } from "date-fns";

export default function WorkersPage() {
  const { data: workers, isLoading, error } = useQuery<WorkerResponse[]>({
    queryKey: ["workers"],
    queryFn: () => api.get<WorkerResponse[]>("/workers"),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Workers"
        description="Distributed worker instances consuming and executing workflow nodes."
      />

      {error ? (
        <div className="p-4 bg-danger-soft border border-danger-border text-danger text-sm">
          Failed to load workers: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-11 bg-surface border border-border" />
          <div className="h-11 bg-surface border border-border" />
        </div>
      ) : workers?.length === 0 ? (
        <EmptyState
          icon={<Icons.Server className="w-10 h-10" />}
          title="No active workers"
          description="Start a worker process to begin consuming jobs from the queue."
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Hostname</Th>
              <Th className="w-24">PID</Th>
              <Th className="w-40">Status</Th>
              <Th className="w-48">Last Heartbeat</Th>
              <Th>Current Job</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {workers?.map((worker) => {
              const lastHeartbeat = new Date(worker.last_heartbeat);
              const isStale = Date.now() - lastHeartbeat.getTime() > 30000;

              return (
                <tr key={worker.id} className="hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{worker.hostname}</td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground-muted">{worker.pid}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {isStale ? (
                        <StatusIcon status="FAILED" className="w-4 h-4" />
                      ) : worker.status === "BUSY" ? (
                        <StatusIcon status="RUNNING" className="w-4 h-4" />
                      ) : (
                        <StatusIcon status="QUEUED" className="w-4 h-4" />
                      )}
                      <span className={`text-xs ${isStale ? "text-danger font-medium" : ""}`}>
                        {isStale ? "STALE" : worker.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground-muted font-mono">
                    {formatDistanceToNow(lastHeartbeat, { addSuffix: true })}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground truncate max-w-[200px]">
                    {worker.current_node_id || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}
