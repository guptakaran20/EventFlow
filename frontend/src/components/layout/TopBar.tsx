"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Icons } from "@/components/icons";
import { ThemeToggle } from "@/components/theme";
import { cn } from "@/components/ui";

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/workflows": "Workflows",
  "/executions": "Executions",
  "/workers": "Workers",
  "/dlq": "Dead Letter Queue",
};

function crumbsFor(pathname: string): { label: string; href: string }[] {
  const base = Object.keys(TITLES).find((k) => pathname.startsWith(k));
  if (!base) return [{ label: "EventFlow", href: "/dashboard" }];
  const crumbs = [{ label: TITLES[base], href: base }];
  const rest = pathname.slice(base.length).split("/").filter(Boolean);
  if (rest.length) {
    const id = rest[rest.length - 1];
    crumbs.push({ label: id, href: pathname });
  }
  return crumbs;
}

export function TopBar({ onMenu }: { onMenu?: () => void }) {
  const pathname = usePathname();
  const [isAuth, setIsAuth] = useState<boolean>(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const { data: me } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.me(),
    retry: false,
  });

  useEffect(() => {
    if (me?.api_key_id) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsAuth(true);
    } else {
      setIsAuth(Boolean(localStorage.getItem("eventflow_auth_status")));
    }
  }, [me]);

  // Backend reachability — piggyback on the metrics query the sidebar already runs
  const { isError, isSuccess } = useQuery({
    queryKey: ["metrics", "summary"],
    queryFn: () => api.get("/metrics/summary"),
    refetchInterval: 5000,
  });

  const online = isSuccess ? true : isError ? false : null;

  const handleLogout = async () => {
    await api.logout();
  };

  const crumbs = crumbsFor(pathname);
  const keyDisplayName = me?.name || "Connected Key";

  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-sm flex items-center px-4 md:px-6 justify-between shrink-0 sticky top-0 z-20 gap-3">
      {/* Left: menu + breadcrumbs */}
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onMenu}
          className="md:hidden p-2 -ml-2 text-foreground-muted hover:text-foreground cursor-pointer"
          aria-label="Open navigation"
        >
          <Icons.Menu className="w-5 h-5" />
        </button>
        <nav className="flex items-center gap-1.5 min-w-0" aria-label="Breadcrumb">
          {crumbs.map((c, i) => (
            <React.Fragment key={c.href}>
              {i > 0 && (
                <Icons.ChevronRight className="w-3.5 h-3.5 text-foreground-faint shrink-0" />
              )}
              {i === crumbs.length - 1 ? (
                <span className="font-serif text-lg tracking-tight truncate">{c.label}</span>
              ) : (
                <Link
                  href={c.href}
                  className="font-serif text-lg tracking-tight text-foreground-muted hover:text-foreground transition-colors truncate"
                >
                  {c.label}
                </Link>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right: status + theme + account */}
      <div className="flex items-center gap-2 md:gap-3 shrink-0">
        {/* Backend status */}
        <div
          className="hidden sm:flex items-center gap-2 h-8 px-3 border border-border bg-surface text-[11px] font-mono text-foreground-muted"
          title={online ? "Backend reachable" : online === false ? "Backend unreachable" : "Checking backend"}
        >
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              online === false
                ? "bg-danger"
                : online
                  ? "bg-green-500 animate-pulse"
                  : "bg-foreground-faint"
            )}
          />
          {online === false ? "Offline" : online ? "Live" : "…"}
        </div>

        <ThemeToggle />

        {/* Account menu */}
        {isAuth && (
          <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 h-8 pl-2.5 pr-2 border border-border bg-surface text-[11px] font-mono text-foreground-muted hover:text-foreground hover:bg-surface-hover transition-colors cursor-pointer"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="w-1.5 h-1.5 bg-foreground rounded-full" />
              <span className="hidden sm:inline">{keyDisplayName}</span>
              <Icons.ChevronDown className={cn("w-3.5 h-3.5 transition-transform", menuOpen && "rotate-180")} />
            </button>

            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} aria-hidden />
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-1.5 w-56 border border-border bg-surface z-20"
                >
                  <div className="px-3 py-3 border-b border-border">
                    <div className="label-caps mb-1.5">API Key</div>
                    <div className="font-mono text-xs text-foreground truncate">{keyDisplayName}</div>
                    <div className="flex items-center gap-1.5 mt-2 text-[11px] font-mono text-foreground-muted">
                      <span
                        className={cn(
                          "w-1.5 h-1.5 rounded-full",
                          online === false ? "bg-danger" : "bg-foreground"
                        )}
                      />
                      {online === false ? "Backend offline" : "Connected"}
                    </div>
                  </div>
                  <button
                    onClick={handleLogout}
                    role="menuitem"
                    className="w-full flex items-center gap-2.5 px-3 h-10 text-sm text-danger hover:bg-danger-soft transition-colors cursor-pointer"
                  >
                    <Icons.Close className="w-3.5 h-3.5" />
                    Disconnect
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
