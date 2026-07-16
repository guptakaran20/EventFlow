"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons } from "@/components/icons";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: Icons.Activity },
  { href: "/workflows", label: "Workflows", icon: Icons.Workflow },
  { href: "/executions", label: "Executions", icon: Icons.Play },
  { href: "/workers", label: "Workers", icon: Icons.Server },
  { href: "/dlq", label: "DLQ", icon: Icons.Archive },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-border bg-background flex flex-col h-full shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <Link href="/" className="flex items-center gap-3">
          <Icons.Workflow className="w-5 h-5 text-brand" />
          <span className="font-semibold text-lg tracking-tight">EventFlow</span>
        </Link>
      </div>
      <nav className="flex-1 py-6 px-4 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2 text-sm transition-colors
                ${isActive 
                  ? "bg-surface-hover text-brand font-medium" 
                  : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"}
              `}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-border">
        <div className="px-3 py-2 text-xs text-foreground-muted">
          v0.1.0-mvp
        </div>
      </div>
    </aside>
  );
}
