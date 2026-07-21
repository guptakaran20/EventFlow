"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { api } from "@/lib/api";
import { Icons } from "@/components/icons";
import { ThemeToggle } from "@/components/theme";

gsap.registerPlugin(useGSAP);

export default function LoginPage() {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoKey, setDemoKey] = useState("");
  const [generatingKey, setGeneratingKey] = useState(false);
  const router = useRouter();
  const root = useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (localStorage.getItem("eventflow_auth_status")) {
      router.push("/dashboard");
    }
  }, [router]);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const strokes = root.current?.querySelectorAll<SVGGeometryElement>(
          "[data-blueprint] circle, [data-blueprint] path"
        );
        strokes?.forEach((s) => {
          const len = s.getTotalLength();
          gsap.set(s, { strokeDasharray: len, strokeDashoffset: len });
        });
        const tl = gsap
          .timeline({ defaults: { ease: "power3.out" } })
          .from("[data-blueprint]", { opacity: 0, scale: 0.9, duration: 1.2 })
          .fromTo("[data-logo]", { opacity: 0, y: 12, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, clearProps: "all" }, "-=0.8")
          .fromTo("[data-title]", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.5, clearProps: "all" }, "-=0.3")
          .fromTo("[data-sub]", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.5, clearProps: "all" }, "-=0.35")
          .fromTo("[data-field]", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, clearProps: "all" }, "-=0.25");
        if (strokes?.length) {
          tl.to(
            strokes,
            { strokeDashoffset: 0, duration: 2, ease: "power1.inOut" },
            0
          );
        }
      });
      return () => mm.revert();
    },
    { scope: root, dependencies: [] }
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const isValid = await api.login(apiKey.trim());
      if (isValid) {
        router.push("/dashboard");
      } else {
        setError("Invalid API key");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateKey = async () => {
    setGeneratingKey(true);
    setError("");
    try {
      const key = await api.createDemoKey();
      setDemoKey(key);
      setApiKey(key);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate demo key");
    } finally {
      setGeneratingKey(false);
    }
  };

  return (
    <div ref={root} className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-5 right-5 z-20">
        <ThemeToggle />
      </div>
      {/* Faint blueprint */}
      <div data-blueprint className="absolute inset-0 pointer-events-none opacity-[0.04] flex items-center justify-center text-foreground">
        <svg viewBox="0 0 800 800" className="w-full max-w-4xl h-auto" stroke="currentColor" fill="none">
          <circle cx="400" cy="400" r="300" strokeWidth="1" />
          <circle cx="400" cy="400" r="200" strokeWidth="1" />
          <path d="M400 100 L400 700 M100 400 L700 400" strokeWidth="1" />
        </svg>
      </div>

      <div className="w-full max-w-sm z-10">
        <div className="mb-12 text-center">
          <div data-logo className="flex justify-center mb-5">
            <Icons.Workflow className="w-8 h-8 text-foreground" />
          </div>
          <Link href="/" data-title className="font-serif text-3xl tracking-tight hover:opacity-80 inline-block cursor-pointer text-foreground">
            EventFlow
          </Link>
          <p data-sub className="text-foreground-muted mt-2 text-sm">
            Enter your API key to connect
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div data-field className="space-y-2">
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
            data-field
            className="w-full bg-inverse text-inverse-foreground px-4 h-11 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer mt-6"
          >
            {loading ? "Authenticating…" : "Proceed to Dashboard"}
          </button>
          
          <div data-field className="text-center mt-4 pt-2 border-t border-border-strong">
            <button
              type="button"
              onClick={handleGenerateKey}
              disabled={generatingKey}
              className="text-sm text-foreground-muted hover:text-foreground underline transition-colors disabled:opacity-50 disabled:no-underline"
            >
              {generatingKey ? "Generating key..." : "Need a key? Generate a API key"}
            </button>
          </div>
        </form>
      </div>

      {demoKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="bg-surface border border-border-strong p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-serif">API Key Generated</h3>
            <p className="text-sm text-foreground-muted">
              Please copy your API key. It will only be shown once. It has been automatically filled in for you.
            </p>
            <div className="bg-background border border-border p-3 font-mono text-sm break-all">
              {demoKey}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(demoKey);
                }}
                className="px-4 py-2 text-sm border border-border hover:bg-surface-hover transition-colors"
              >
                Copy
              </button>
              <button
                type="button"
                onClick={() => setDemoKey("")}
                className="px-4 py-2 text-sm bg-inverse text-inverse-foreground hover:opacity-90 transition-opacity"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
