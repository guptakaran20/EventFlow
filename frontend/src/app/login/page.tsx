"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Icons } from "@/components/icons";

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
      {/* Background illustration hints */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] flex items-center justify-center">
        <svg viewBox="0 0 800 800" className="w-full max-w-4xl h-auto" stroke="currentColor" fill="none">
          <circle cx="400" cy="400" r="300" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="400" cy="400" r="200" strokeWidth="1" />
          <path d="M400 100 L400 700 M100 400 L700 400" strokeWidth="1" />
        </svg>
      </div>

      <div className="w-full max-w-sm z-10">
        <div className="mb-12 text-center">
          <div className="flex justify-center mb-6">
            <Icons.Workflow className="w-10 h-10 text-brand" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">EventFlow</h1>
          <p className="text-foreground-muted mt-2 text-sm">Orchestration Engine</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="apiKey" className="text-sm font-medium text-foreground-muted">
              API Key
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full bg-surface border border-border px-4 py-2 text-sm focus:outline-none focus:border-brand transition-colors font-mono"
              placeholder="ef_..."
              required
            />
          </div>

          {error && (
            <div className="text-sm text-red-500 border border-red-500/20 bg-red-500/5 px-4 py-2 flex items-center gap-2">
              <Icons.Close className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !apiKey}
            className="w-full bg-brand hover:bg-brand-hover text-white px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Authenticating..." : "Connect"}
          </button>
        </form>
      </div>
    </div>
  );
}
