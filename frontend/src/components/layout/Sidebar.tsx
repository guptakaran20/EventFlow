"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons } from "@/components/icons";
import { cn } from "@/components/ui";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: Icons.Activity },
  { href: "/workflows", label: "Workflows", icon: Icons.Workflow },
  { href: "/executions", label: "Executions", icon: Icons.Play },
  { href: "/workers", label: "Workers", icon: Icons.Server },
  { href: "/dlq", label: "DLQ", icon: Icons.Archive },
];

export function Sidebar({
  open,
  onClose,
}: {
  open?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();

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
          "fixed z-40 inset-y-0 left-0 w-60 border-r border-border bg-background flex flex-col h-full shrink-0 transition-transform duration-200",
          "md:static md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="h-16 flex items-center px-5 border-b border-border">
          <Link href="/" className="flex items-center gap-2.5 group">
            <Icons.Workflow className="w-5 h-5 text-foreground" />
            <span className="font-serif text-lg tracking-tight">EventFlow</span>
          </Link>
        </div>
        <nav className="flex-1 py-5 px-3 flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "relative flex items-center gap-3 px-3 h-9 text-sm transition-colors duration-150",
                  isActive
                    ? "text-foreground font-medium bg-surface-hover"
                    : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-foreground" />
                )}
                <item.icon className="w-4 h-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border">
          <div className="label-caps">v0.1.0 — MVP</div>
        </div>
      </aside>
    </>
  );
}
