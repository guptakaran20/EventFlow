"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MetricsSummaryResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";

function MetricCard({ title, value, icon, className = "" }: { title: string, value: number | string, icon?: React.ReactNode, className?: string }) {
  return (
    <div className={`border border-border bg-surface p-5 flex flex-col justify-between ${className}`}>
      <div className="flex items-center justify-between text-foreground-muted mb-4">
        <span className="text-sm font-medium">{title}</span>
        {icon && <div className="text-foreground-muted opacity-50">{icon}</div>}
      </div>
      <div className="text-3xl font-semibold tracking-tight text-foreground">
        {value}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useQuery<MetricsSummaryResponse>({
    queryKey: ["metrics", "summary"],
    queryFn: () => api.get<MetricsSummaryResponse>("/metrics/summary"),
    refetchInterval: 5000,
  });

  if (error) {
    return (
      <div className="p-6 bg-red-500/5 border border-red-500/20 text-red-500 flex items-center gap-2">
        <Icons.Close className="w-4 h-4 shrink-0" />
        Failed to load metrics: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-medium tracking-tight">Overview</h2>
        <div className="text-sm text-foreground-muted flex items-center gap-2">
          {isLoading ? (
            <span className="animate-pulse">Loading...</span>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Live updates active
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Executions"
          value={metrics?.active_executions ?? "-"}
          icon={<StatusIcon status="RUNNING" className="w-5 h-5 !text-foreground-muted" />}
        />
        <MetricCard
          title="Queue Depth"
          value={metrics?.queue_depth ?? "-"}
          icon={<StatusIcon status="QUEUED" className="w-5 h-5 !text-foreground-muted" />}
        />
        <MetricCard
          title="Active Workers"
          value={metrics?.active_workers ?? "-"}
          icon={<Icons.Server className="w-5 h-5" />}
        />
        <MetricCard
          title="Dead Letter Jobs"
          value={metrics?.dead_letter_jobs ?? "-"}
          icon={<StatusIcon status="DEAD_LETTERED" className="w-5 h-5 !text-red-500" />}
          className={metrics?.dead_letter_jobs ? "border-red-500/50" : ""}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="border border-border bg-surface p-6 min-h-[300px]">
          <h3 className="text-sm font-medium text-foreground-muted mb-6">Recent Activity</h3>
          {/* Recent activity will go here, for now it's just a placeholder */}
          <div className="flex flex-col items-center justify-center h-48 text-foreground-muted">
            <Icons.Activity className="w-8 h-8 mb-4 opacity-20" />
            <span className="text-sm">Activity feed empty</span>
          </div>
        </div>
        
        <div className="border border-border bg-surface p-6 min-h-[300px]">
          <h3 className="text-sm font-medium text-foreground-muted mb-6">System Health</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-sm">Running Nodes</span>
              <span className="font-mono">{metrics?.running_nodes ?? "-"}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-sm">Queued Nodes</span>
              <span className="font-mono">{metrics?.queued_nodes ?? "-"}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-sm">Total Connected Workers</span>
              <span className="font-mono">{metrics?.workers ?? "-"}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
