"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MetricsSummaryResponse, ExecutionResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { Panel } from "@/components/ui";

function Metric({
  label,
  value,
  danger,
}: {
  label: string;
  value: number | string;
  danger?: boolean;
}) {
  return (
    <div className="px-5 py-4 flex flex-col gap-2 border-r border-border last:border-r-0">
      <span className="label-caps">{label}</span>
      <span
        className={`font-serif text-3xl tracking-tight tabular-nums ${
          danger ? "text-danger" : "text-foreground"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useQuery<MetricsSummaryResponse>({
    queryKey: ["metrics", "summary"],
    queryFn: () => api.get<MetricsSummaryResponse>("/metrics/summary"),
    refetchInterval: 5000,
  });

  const { data: executions } = useQuery<ExecutionResponse[]>({
    queryKey: ["executions"],
    queryFn: () => api.get<ExecutionResponse[]>("/executions?limit=6"),
    refetchInterval: 5000,
  });

  if (error) {
    return (
      <div className="p-4 bg-danger-soft border border-danger-border text-danger flex items-center gap-2 text-sm">
        <Icons.Close className="w-4 h-4 shrink-0" />
        Failed to load metrics: {(error as Error).message}
      </div>
    );
  }

  const v = (n?: number) => (isLoading ? "—" : (n ?? 0));

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="label-caps mb-2">Operational Command Center</div>
          <h1 className="font-serif text-3xl md:text-4xl tracking-tight leading-none">
            Overview
          </h1>
        </div>
        <div className="text-xs text-foreground-muted flex items-center gap-2 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-foreground animate-pulse" />
          Live · 5s
        </div>
      </div>

      {/* Metric strip */}
      <Panel className="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 divide-border">
        <Metric label="Active Executions" value={v(metrics?.active_executions)} />
        <Metric label="Queue Depth" value={v(metrics?.queue_depth)} />
        <Metric label="Active Workers" value={v(metrics?.active_workers)} />
        <Metric
          label="Dead Letter"
          value={v(metrics?.dead_letter_jobs)}
          danger={!!metrics?.dead_letter_jobs}
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Recent activity */}
        <Panel className="lg:col-span-3 flex flex-col">
          <div className="px-5 h-11 flex items-center justify-between border-b border-border bg-surface-2">
            <span className="label-caps">Recent Executions</span>
            <Link
              href="/executions"
              className="text-xs text-foreground-muted hover:text-foreground transition-colors"
            >
              View all →
            </Link>
          </div>
          {executions && executions.length > 0 ? (
            <div className="divide-y divide-border">
              {executions.map((ex) => (
                <Link
                  key={ex.id}
                  href={`/executions/${ex.id}`}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover transition-colors group"
                >
                  <StatusIcon status={ex.status} />
                  <span className="font-mono text-xs truncate flex-1">{ex.id}</span>
                  <span className="label-caps">{ex.status}</span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-foreground-faint">
              <Icons.Activity className="w-7 h-7 mb-3 opacity-50" />
              <span className="text-sm">No executions yet</span>
            </div>
          )}
        </Panel>

        {/* System health */}
        <Panel className="lg:col-span-2 flex flex-col">
          <div className="px-5 h-11 flex items-center border-b border-border bg-surface-2">
            <span className="label-caps">System Health</span>
          </div>
          <div className="px-5 py-2">
            {[
              ["Running Nodes", metrics?.running_nodes],
              ["Queued Nodes", metrics?.queued_nodes],
              ["Connected Workers", metrics?.workers],
            ].map(([label, val]) => (
              <div
                key={label as string}
                className="flex justify-between items-center py-3 border-b border-border last:border-b-0"
              >
                <span className="text-sm text-foreground-muted">{label}</span>
                <span className="font-mono text-sm tabular-nums">
                  {v(val as number)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
