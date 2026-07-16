"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MetricsSummaryResponse } from "@/lib/types";
import { Icons } from "@/components/icons";
import { cn } from "@/components/ui";

type BadgeKey = "active_executions" | "dead_letter_jobs" | "active_workers";

type NavItem = {
  href: string;
  label: string;
  icon: (props: any) => React.ReactElement;
  badge?: BadgeKey;
  danger?: boolean;
};

type NavGroup = { heading: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    heading: "Monitor",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: Icons.Activity },
      { href: "/executions", label: "Executions", icon: Icons.Play, badge: "active_executions" },
    ],
  },
  {
    heading: "Build",
    items: [
      { href: "/workflows", label: "Workflows", icon: Icons.Workflow },
      { href: "/workflows/new", label: "Create Workflow", icon: Icons.Plus },
    ],
  },
  {
    heading: "Operate",
    items: [
      { href: "/workers", label: "Workers", icon: Icons.Server, badge: "active_workers" },
      { href: "/dlq", label: "DLQ", icon: Icons.Archive, badge: "dead_letter_jobs", danger: true },
    ],
  },
];

export function Sidebar({
  open,
  onClose,
  collapsed = false,
  onToggleCollapse,
}: {
  open?: boolean;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();

  let bestMatch = "";
  NAV.forEach((group) => {
    group.items.forEach((item) => {
      if (pathname.startsWith(item.href) && item.href.length > bestMatch.length) {
        bestMatch = item.href;
      }
    });
  });

  const { data: metrics } = useQuery<MetricsSummaryResponse>({
    queryKey: ["metrics", "summary"],
    queryFn: () => api.get<MetricsSummaryResponse>("/metrics/summary"),
    refetchInterval: 5000,
  });

  const badgeValue = (key?: BadgeKey) =>
    key && metrics ? metrics[key] ?? 0 : 0;

  return (
    <>
      {/* Mobile scrim */}
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/30 backdrop-blur-[1px] transition-opacity duration-200 md:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
        aria-hidden
      />
      <aside
        className={cn(
          "fixed z-40 inset-y-0 left-0 border-r border-border bg-background flex flex-col h-full shrink-0",
          "transition-transform duration-200 md:transition-[width] md:duration-200",
          "md:static md:translate-x-0",
          collapsed ? "w-60 md:w-[4.5rem]" : "w-60",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand */}
        <div
          className={cn(
            "h-16 flex items-center border-b border-border shrink-0",
            collapsed ? "md:justify-center px-5 md:px-0" : "px-5"
          )}
        >
          <Link href="/" className="flex items-center gap-2.5 group" onClick={onClose}>
            <Icons.Workflow className="w-5 h-5 text-foreground shrink-0" />
            <span
              className={cn(
                "font-serif text-lg tracking-tight whitespace-nowrap",
                collapsed && "md:hidden"
              )}
            >
              EventFlow
            </span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-5">
          {NAV.map((group) => (
            <div key={group.heading} className="flex flex-col gap-0.5">
              <div
                className={cn(
                  "label-caps px-3 mb-1.5 h-4",
                  collapsed && "md:opacity-0 md:h-2 md:mb-0"
                )}
              >
                {group.heading}
              </div>
              {group.items.map((item) => {
                const isActive = item.href === bestMatch;
                const badge = badgeValue(item.badge);
                const showBadge = badge > 0;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "relative flex items-center gap-3 px-3 h-9 text-sm transition-colors duration-150 group",
                      collapsed && "md:justify-center md:px-0",
                      isActive
                        ? "text-foreground font-medium bg-surface-hover"
                        : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-foreground" />
                    )}
                    <span className="relative shrink-0">
                      <item.icon className="w-4 h-4" />
                      {/* collapsed: badge as dot on icon */}
                      {showBadge && collapsed && (
                        <span
                          className={cn(
                            "absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full hidden md:block",
                            item.danger ? "bg-danger" : "bg-foreground"
                          )}
                        />
                      )}
                    </span>
                    <span className={cn("whitespace-nowrap", collapsed && "md:hidden")}>
                      {item.label}
                    </span>
                    {showBadge && (
                      <span
                        className={cn(
                          "ml-auto min-w-5 h-5 px-1.5 inline-flex items-center justify-center text-[11px] font-mono tabular-nums border",
                          collapsed && "md:hidden",
                          item.danger
                            ? "text-danger border-danger-border bg-danger-soft"
                            : "text-foreground-muted border-border bg-surface-2"
                        )}
                      >
                        {badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-border p-3 flex flex-col gap-1">
          <button
            onClick={onToggleCollapse}
            className={cn(
              "hidden md:flex items-center gap-3 px-3 h-9 text-sm text-foreground-muted hover:text-foreground hover:bg-surface-hover transition-colors cursor-pointer",
              collapsed && "md:justify-center md:px-0"
            )}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icons.ChevronRight
              className={cn("w-4 h-4 shrink-0 transition-transform", !collapsed && "rotate-180")}
            />
            <span className={cn("whitespace-nowrap", collapsed && "md:hidden")}>Collapse</span>
          </button>
          <div className={cn("label-caps px-3 py-1", collapsed && "md:hidden")}>
            v0.1.0 — MVP
          </div>
        </div>
      </aside>
    </>
  );
}
