"use client";

import React, { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Icons } from "@/components/icons";
import { ThemeToggle } from "@/components/theme";

const TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/workflows": "Workflows",
  "/executions": "Executions",
  "/workers": "Workers",
  "/dlq": "Dead Letter Queue",
};

function titleFor(pathname: string): string {
  const match = Object.keys(TITLES).find((k) => pathname.startsWith(k));
  return match ? TITLES[match] : "EventFlow";
}

export function TopBar({ onMenu }: { onMenu?: () => void }) {
  const router = useRouter();
  const pathname = usePathname();
  const [apiKey, setApiKey] = useState<string | null>(null);

  useEffect(() => {
    setApiKey(localStorage.getItem("eventflow_api_key"));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("eventflow_api_key");
    router.push("/login");
  };

  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-sm flex items-center px-4 md:px-6 justify-between shrink-0 sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenu}
          className="md:hidden p-2 -ml-2 text-foreground-muted hover:text-foreground cursor-pointer"
          aria-label="Open navigation"
        >
          <Icons.Menu className="w-5 h-5" />
        </button>
        <span className="label-caps hidden sm:block">EventFlow /</span>
        <h2 className="font-serif text-lg tracking-tight">{titleFor(pathname)}</h2>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        {apiKey && (
          <div className="flex items-center gap-2 pl-3 pr-2 h-8 bg-surface border border-border text-[11px] font-mono text-foreground-muted">
            <span className="w-1.5 h-1.5 bg-foreground rounded-full" />
            <span className="hidden sm:inline">API key active</span>
            <button
              onClick={handleLogout}
              className="ml-1 p-1 hover:text-foreground cursor-pointer"
              title="Disconnect"
            >
              <Icons.Close className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
