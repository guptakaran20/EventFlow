"use client";

import React, { useRef } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { api } from "@/lib/api";
import { MetricsSummaryResponse, ExecutionResponse } from "@/lib/types";
import { Icons, StatusIcon } from "@/components/icons";
import { Panel } from "@/components/ui";

gsap.registerPlugin(useGSAP);

/** Number that animates (count-up) to its value whenever it changes. */
function CountUp({
  value,
  className = "",
  loading,
}: {
  value?: number;
  className?: string;
  loading?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      if (loading || value == null || !ref.current) return;
      const el = ref.current;
      const obj = { n: Number(el.dataset.prev ?? 0) };
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.to(obj, {
          n: value,
          duration: 0.8,
          ease: "power2.out",
          onUpdate: () => {
            el.textContent = String(Math.round(obj.n));
          },
        });
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        el.textContent = String(value);
      });

      el.dataset.prev = String(value);
      return () => mm.revert();
    },
    { dependencies: [value, loading], scope: ref }
  );

  return (
    <span ref={ref} className={className}>
      {loading ? "—" : (value ?? 0)}
    </span>
  );
}

function MetricTile({
  label,
  value,
  loading,
  danger,
  hint,
}: {
  label: string;
  value?: number;
  loading?: boolean;
  danger?: boolean;
  hint?: string;
}) {
  return (
    <div
      data-tile
      className="relative px-5 py-6 flex flex-col gap-3 border-r border-b md:border-b-0 border-border last:border-r-0 overflow-hidden"
    >
      <div className="flex items-center justify-between">
        <span className="label-caps">{label}</span>
        {danger && !loading && value ? (
          <span className="w-1.5 h-1.5 bg-danger animate-pulse" />
        ) : null}
      </div>
      <CountUp
        value={value}
        loading={loading}
        className={`font-serif text-4xl md:text-5xl tracking-tight tabular-nums leading-none ${
          danger && value ? "text-danger" : "text-foreground"
        }`}
      />
      {hint && <span className="text-xs text-foreground-faint">{hint}</span>}
    </div>
  );
}

export default function DashboardPage() {
  const root = useRef<HTMLDivElement>(null);

  const { data: metrics, isLoading, error } = useQuery<MetricsSummaryResponse>({
    queryKey: ["metrics", "summary"],
    queryFn: () => api.get<MetricsSummaryResponse>("/metrics/summary"),
    refetchInterval: 5000,
  });

  const { data: executions } = useQuery<ExecutionResponse[]>({
    queryKey: ["executions"],
    queryFn: () => api.get<ExecutionResponse[]>("/executions?limit=7"),
    refetchInterval: 5000,
  });

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap
          .timeline({ defaults: { ease: "power2.out" } })
          .from(".dash-head", { opacity: 0, y: 16, duration: 0.5 })
          .from("[data-tile]", { opacity: 0, y: 20, duration: 0.5, stagger: 0.08 }, "-=0.2")
          .from("[data-panel]", { opacity: 0, y: 24, duration: 0.6, stagger: 0.1 }, "-=0.2");
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  // Stagger execution rows as they arrive / change
  const rowsKey = executions?.map((e) => e.id).join(",");
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from("[data-exec-row]", {
          opacity: 0,
          x: -8,
          duration: 0.4,
          stagger: 0.04,
          ease: "power1.out",
        });
      });
      return () => mm.revert();
    },
    { dependencies: [rowsKey], scope: root }
  );

  if (error) {
    return (
      <div className="p-4 bg-danger-soft border border-danger-border text-danger flex items-center gap-2 text-sm">
        <Icons.Close className="w-4 h-4 shrink-0" />
        Failed to load metrics: {(error as Error).message}
      </div>
    );
  }

  const health: [string, number | undefined][] = [
    ["Running Nodes", metrics?.running_nodes],
    ["Queued Nodes", metrics?.queued_nodes],
    ["Total Workers (All-Time)", metrics?.workers],
    ["Active Workers (Alive)", metrics?.active_workers],
  ];

  return (
    <div ref={root} className="space-y-8">
      {/* Header */}
      <div className="dash-head flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="label-caps mb-3">Operational Command Center</div>
          <h1 className="font-serif text-4xl md:text-5xl tracking-tight leading-none">
            Overview
          </h1>
        </div>
        <div className="flex items-center gap-2 text-xs text-foreground-muted font-mono border border-border bg-surface px-3 h-8">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          Live · Refreshing every 5 seconds
        </div>
      </div>

      {/* Metric tiles */}
      <Panel className="grid grid-cols-2 md:grid-cols-4">
        <MetricTile
          label="Active Executions"
          value={metrics?.active_executions}
          loading={isLoading}
          hint="in progress"
        />
        <MetricTile
          label="Queue Depth"
          value={metrics?.queued_nodes}
          loading={isLoading}
          hint="jobs waiting"
        />
        <MetricTile
          label="Active Workers"
          value={metrics?.active_workers}
          loading={isLoading}
          hint="consuming"
        />
        <MetricTile
          label="Dead Letter"
          value={metrics?.dead_letter_jobs}
          loading={isLoading}
          danger
          hint="needs attention"
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Recent executions */}
        <Panel data-panel className="lg:col-span-3 flex flex-col">
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
              {executions.map((ex) => {
                const danger = ["FAILED", "DEAD_LETTERED", "PARTIAL_FAILED"].includes(
                  ex.status
                );
                return (
                  <Link
                    key={ex.id}
                    href={`/executions/${ex.id}`}
                    data-exec-row
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-surface-hover transition-colors group"
                  >
                    <StatusIcon status={ex.status} />
                    <span className="font-mono text-xs truncate flex-1 group-hover:underline underline-offset-2">
                      {ex.id}
                    </span>
                    <span
                      className={`text-[11px] font-mono uppercase tracking-wide ${
                        danger ? "text-danger" : "text-foreground-faint"
                      }`}
                    >
                      {ex.status}
                    </span>
                    <Icons.ChevronRight className="w-3.5 h-3.5 text-foreground-faint opacity-0 group-hover:opacity-100 transition-opacity" />
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-foreground-faint">
              <Icons.Activity className="w-8 h-8 mb-3 opacity-50" />
              <span className="text-sm">No executions yet</span>
              <Link
                href="/workflows"
                className="mt-4 text-xs text-foreground-muted hover:text-foreground transition-colors underline underline-offset-2"
              >
                Create a workflow →
              </Link>
            </div>
          )}
        </Panel>

        {/* System health */}
        <Panel data-panel className="lg:col-span-2 flex flex-col">
          <div className="px-5 h-11 flex items-center border-b border-border bg-surface-2">
            <span className="label-caps">System Health</span>
          </div>
          <div className="px-5 py-2">
            {health.map(([label, val]) => (
              <div
                key={label}
                className="flex justify-between items-center py-3.5 border-b border-border last:border-b-0"
              >
                <span className="text-sm text-foreground-muted">{label}</span>
                <CountUp
                  value={val}
                  loading={isLoading}
                  className="font-mono text-sm tabular-nums"
                />
              </div>
            ))}
          </div>
          <div className="mt-auto px-5 py-4 border-t border-border">
            <Link
              href="/workers"
              className="text-xs text-foreground-muted hover:text-foreground transition-colors"
            >
              Inspect workers →
            </Link>
          </div>
        </Panel>
      </div>
    </div>
  );
}
