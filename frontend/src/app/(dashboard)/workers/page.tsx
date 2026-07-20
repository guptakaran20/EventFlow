"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WorkerResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { PageHeader, Table, Th, EmptyState, Button } from "@/components/ui";
import { formatDistanceToNow } from "date-fns";
import { usePageReveal, useRowStagger } from "@/lib/reveal";

export default function WorkersPage() {
  const { data: workers, isLoading, error } = useQuery<WorkerResponse[]>({
    queryKey: ["workers"],
    queryFn: () => api.get<WorkerResponse[]>("/workers"),
    refetchInterval: 5000,
  });

  const queryClient = useQueryClient();

  const spawnMutation = useMutation({
    mutationFn: async () => {
      return api.post("/workers/spawn", {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workers"] });
    },
  });

  const root = usePageReveal<HTMLDivElement>();
  const rowsKey = workers?.map((w) => w.worker_id).join(",");
  const tbodyScope = useRowStagger<HTMLTableSectionElement>(rowsKey, "[data-row]");

  return (
    <div ref={root} className="space-y-8">
      <div data-reveal-head className="flex justify-between items-start gap-4 flex-wrap">
        <PageHeader
          title="Workers"
          description="Distributed worker instances consuming and executing workflow nodes."
        />
        <Button
          variant="primary"
          onClick={() => spawnMutation.mutate()}
          disabled={spawnMutation.isPending}
          className="h-9 px-4 mt-2"
        >
          {spawnMutation.isPending ? "Spawning..." : "Spawn Worker"}
        </Button>
      </div>

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
              <Th className="w-40">Status</Th>
              <Th className="w-48">Last Heartbeat</Th>
              <Th>Current Job</Th>
            </tr>
          </thead>
          <tbody ref={tbodyScope} className="divide-y divide-border">
            {workers?.filter((worker) => {
              const isStale = worker.heartbeat_age_seconds !== null && worker.heartbeat_age_seconds > 30;
              return !isStale && worker.status !== "OFFLINE";
            }).map((worker) => {
              const lastHeartbeat = worker.last_heartbeat_at ? new Date(worker.last_heartbeat_at) : null;

              return (
                <tr key={worker.worker_id} data-row className="hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{worker.hostname}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {worker.status === "BUSY" ? (
                        <StatusIcon status="RUNNING" className="w-4 h-4" />
                      ) : (
                        <StatusIcon status="QUEUED" className="w-4 h-4" />
                      )}
                      <span className="text-xs">
                        {worker.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground-muted font-mono">
                    {lastHeartbeat ? formatDistanceToNow(lastHeartbeat, { addSuffix: true }) : "Never"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground truncate max-w-[200px]">
                    {worker.current_job_id || "—"}
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
