"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icons } from "@/components/icons";

export function TopBar({ title }: { title?: string }) {
  const router = useRouter();
  const [apiKey, setApiKey] = useState<string | null>(null);

  useEffect(() => {
    setApiKey(localStorage.getItem("eventflow_api_key"));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("eventflow_api_key");
    router.push("/login");
  };

  return (
    <header className="h-16 border-b border-border bg-surface flex items-center px-6 justify-between shrink-0">
      <h1 className="text-lg font-medium">{title}</h1>
      <div className="flex items-center gap-4">
        {apiKey && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border text-xs font-mono text-foreground-muted">
            API Key Active
            <button onClick={handleLogout} className="ml-2 hover:text-foreground" title="Logout">
              <Icons.Close className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
