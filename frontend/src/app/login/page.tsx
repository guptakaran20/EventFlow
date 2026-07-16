"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Icons } from "@/components/icons";
import { ThemeToggle } from "@/components/theme";

export default function LoginPage() {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      localStorage.setItem("eventflow_api_key", apiKey);
      const isValid = await api.verifyAuth();
      if (isValid) {
        router.push("/dashboard");
      } else {
        setError("Invalid API key");
        localStorage.removeItem("eventflow_api_key");
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed");
      localStorage.removeItem("eventflow_api_key");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-5 right-5 z-20">
        <ThemeToggle />
      </div>
      {/* Faint blueprint */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.04] flex items-center justify-center text-foreground">
        <svg viewBox="0 0 800 800" className="w-full max-w-4xl h-auto" stroke="currentColor" fill="none">
          <circle cx="400" cy="400" r="300" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="400" cy="400" r="200" strokeWidth="1" />
          <path d="M400 100 L400 700 M100 400 L700 400" strokeWidth="1" />
        </svg>
      </div>

      <div className="w-full max-w-sm z-10">
        <div className="mb-12 text-center">
          <div className="flex justify-center mb-5">
            <Icons.Workflow className="w-8 h-8 text-foreground" />
          </div>
          <h1 className="font-serif text-3xl tracking-tight">EventFlow</h1>
          <p className="text-foreground-muted mt-2 text-sm">
            Enter your API key to connect
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="apiKey" className="label-caps block">
              API Key
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full bg-surface border border-border-strong px-4 h-11 text-sm focus:outline-none focus:border-foreground transition-colors font-mono"
              placeholder="ef_..."
              required
            />
          </div>

          {error && (
            <div className="text-sm text-danger border border-danger-border bg-danger-soft px-4 py-2.5 flex items-center gap-2">
              <Icons.Close className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !apiKey}
            className="w-full bg-inverse text-inverse-foreground px-4 h-11 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? "Authenticating…" : "Connect"}
          </button>
        </form>
      </div>
    </div>
  );
}
