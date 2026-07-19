"use client";

import React, { useRef } from "react";
import Link from "next/link";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { Icons } from "@/components/icons";
import { ThemeToggle } from "@/components/theme";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const CAPABILITIES = [
  {
    title: "Distributed execution",
    body: "Nodes run across multiple worker processes coordinated through Redis Streams consumer groups. Scale out by starting more workers.",
  },
  {
    title: "Retries & dead-letter recovery",
    body: "Per-node retry policies with exponential backoff. Exhausted failures move to a dead-letter queue for inspection and manual replay.",
  },
  {
    title: "Crash recovery",
    body: "Worker heartbeats and stuck-job claiming mean a killed worker mid-job is recovered by another. At-least-once delivery by design.",
  },
  {
    title: "Immutable versioning",
    body: "Every saved workflow becomes an immutable version. Running executions never change when a definition is edited.",
  },
  {
    title: "Live observability",
    body: "WebSocket-driven execution detail. Watch node state transitions, logs, and worker activity stream in as the system operates.",
  },
  {
    title: "Extensible executors",
    body: "HTTP, delay, condition, transform, and webhook nodes ship built-in. New node types register through a small executor registry — no arbitrary code.",
  },
];

const FLOW = [
  ["01", "Define", "Author a workflow as a JSON DAG. The backend validates nodes, edges, executor types, and rejects cycles."],
  ["02", "Version", "A validated definition is stored as an immutable version, ready to execute repeatedly and reproducibly."],
  ["03", "Execute", "Start an execution. Root nodes become execution records; ready nodes publish to Redis Streams."],
  ["04", "Distribute", "Workers consume jobs through a consumer group, run the matching executor, and transition state in PostgreSQL."],
  ["05", "Recover", "Successful nodes unlock downstream nodes. Failures retry per policy, then dead-letter. Crashed workers are recovered."],
  ["06", "Observe", "Every transition is auditable and streamed live over WebSocket to the dashboard."],
];

const CONCEPTS: [string, string][] = [
  ["Workflow", "Logical automation owned by a client."],
  ["Version", "Immutable definition used by executions."],
  ["Execution", "One run of one workflow version."],
  ["Node", "A single step in the workflow DAG."],
  ["Executor", "Module responsible for a node type."],
  ["Worker", "Process consuming jobs and running nodes."],
  ["DLQ", "Queue for jobs that exhaust retries."],
  ["Stream", "Redis queue of ready node jobs."],
];

const STACK = ["FastAPI", "PostgreSQL", "Redis Streams", "WebSocket", "gRPC", "Docker"];

import { useRouter } from "next/navigation";

export default function HomePage() {
  const root = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Redirect removed: users can view homepage even if logged in.


  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        // Hero intro
        gsap
          .timeline({ defaults: { ease: "power2.out" } })
          .from(".hero-eyebrow", { opacity: 0, y: 12, duration: 0.5 })
          .from(".hero-line", { opacity: 0, y: 28, duration: 0.7, stagger: 0.1 }, "-=0.2")
          .from(".hero-lede", { opacity: 0, y: 20, duration: 0.6 }, "-=0.4")
          .from(".hero-cta", { opacity: 0, y: 16, duration: 0.5, stagger: 0.08 }, "-=0.3")
          .from(".hero-meta", { opacity: 0, duration: 0.6 }, "-=0.2");

        // Blueprint reveal + persistent pulse
        gsap.from(".bp-stroke", {
          opacity: 0,
          duration: 1.2,
          stagger: 0.04,
          ease: "power1.out",
          delay: 0.3,
        });
        gsap.to(".bp-pulse", {
          opacity: 0.15,
          scale: 1.6,
          transformOrigin: "center",
          duration: 1.8,
          repeat: -1,
          yoyo: true,
          stagger: 0.4,
          ease: "sine.inOut",
        });

        // Section reveals
        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((el) => {
          gsap.from(el, {
            opacity: 0,
            y: 24,
            duration: 0.6,
            ease: "power2.out",
            scrollTrigger: { trigger: el, start: "top 85%" },
          });
        });

        // Staggered children (grids, lists)
        gsap.utils.toArray<HTMLElement>("[data-stagger]").forEach((el) => {
          gsap.from(el.children, {
            opacity: 0,
            y: 20,
            duration: 0.5,
            stagger: 0.07,
            ease: "power2.out",
            scrollTrigger: { trigger: el, start: "top 80%" },
          });
        });
      });

      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <div ref={root} className="bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Icons.Workflow className="w-5 h-5" />
            <span className="font-serif text-lg tracking-tight">EventFlow</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm text-foreground-muted">
            <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
            <a href="#capabilities" className="hover:text-foreground transition-colors">Capabilities</a>
            <a href="#concepts" className="hover:text-foreground transition-colors">Concepts</a>
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle className="hidden sm:inline-flex" />
            <Link
              href="/login"
              className="inline-flex items-center h-9 px-4 bg-inverse text-inverse-foreground text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Connect
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 md:px-10 grid lg:grid-cols-2 gap-12 lg:gap-8 items-center pt-16 md:pt-24 pb-20 md:pb-28">
        <div>
          <div className="hero-eyebrow label-caps mb-6">Distributed Workflow Orchestration Engine</div>
          <h1 className="font-serif text-[2.6rem] md:text-6xl leading-[1.03] tracking-tight">
            <span className="hero-line block">Reliable workflows,</span>
            <span className="hero-line block">observed in real time.</span>
          </h1>
          <p className="hero-lede text-base md:text-lg text-foreground-muted mt-7 max-w-lg leading-relaxed">
            EventFlow runs multi-step backend jobs as directed acyclic graphs across
            distributed workers — with retries, dead-letter recovery, immutable
            versioning, and live execution monitoring. Infrastructure software, not
            an automation clone.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-9">
            <Link
              href="/login"
              className="hero-cta inline-flex items-center justify-center h-11 px-6 bg-inverse text-inverse-foreground text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Connect Instance
            </Link>

          </div>
        </div>

        {/* Blueprint */}
        <div className="relative aspect-square w-full max-w-[520px] mx-auto lg:mx-0">
          <svg viewBox="0 0 500 500" fill="none" className="w-full h-full">
            <pattern id="g" width="25" height="25" patternUnits="userSpaceOnUse">
              <path d="M25 0 L0 0 0 25" className="stroke-border" strokeWidth="0.5" strokeOpacity="0.5" />
            </pattern>
            <rect width="500" height="500" fill="url(#g)" />
            <g className="stroke-border-strong" strokeWidth="1">
              <circle className="bp-stroke" cx="250" cy="250" r="70" />
              <circle className="bp-stroke" cx="250" cy="250" r="108" strokeDasharray="3 5" />
              <path className="bp-stroke" d="M250 180 L250 90 L120 90" />
              <path className="bp-stroke" d="M250 320 L250 410 L380 410" />
              <path className="bp-stroke" d="M320 250 L430 250 L430 140" />
              <path className="bp-stroke" d="M180 250 L70 250 L70 360" />
              <rect className="bp-stroke" x="100" y="70" width="40" height="40" />
              <rect className="bp-stroke" x="360" y="390" width="40" height="40" />
              <rect className="bp-stroke" x="410" y="120" width="40" height="40" />
              <rect className="bp-stroke" x="50" y="340" width="40" height="40" />
            </g>
            <g className="fill-foreground">
              <circle className="bp-pulse" cx="250" cy="90" r="4" />
              <circle className="bp-pulse" cx="430" cy="250" r="4" />
              <circle className="bp-pulse" cx="70" cy="250" r="4" />
              <circle className="bp-pulse" cx="250" cy="410" r="4" />
              <rect x="242" y="242" width="16" height="16" />
            </g>
          </svg>
        </div>
      </section>

      {/* Problem */}
      <section className="border-t border-border bg-surface-2">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-28 grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4" data-reveal>
            <div className="label-caps mb-4">The Problem</div>
            <h2 className="font-serif text-3xl md:text-4xl leading-tight tracking-tight">
              Multi-step jobs don&apos;t fit a request.
            </h2>
          </div>
          <div className="lg:col-span-8 grid sm:grid-cols-2 gap-x-10 gap-y-8 text-sm leading-relaxed text-foreground-muted" data-stagger>
            <p>Long-running work — API calls, waits, branching, transforms, webhooks — outlives the HTTP request/response lifecycle it&apos;s often trapped in.</p>
            <p>When a step fails, you need to know <span className="text-foreground">exactly which one</span>, why, how many times it retried, and whether it was recovered or abandoned.</p>
            <p>Tools like Airflow and Temporal are powerful but heavy. Spinning them up to run a five-node job is disproportionate.</p>
            <p>EventFlow keeps the serious parts — distributed execution, retries, DLQ, crash recovery, live state — in a small, legible core.</p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-28">
        <div className="max-w-2xl" data-reveal>
          <div className="label-caps mb-4">How It Works</div>
          <h2 className="font-serif text-3xl md:text-5xl leading-[1.05] tracking-tight">
            From JSON definition to live execution.
          </h2>
          <p className="text-foreground-muted mt-5 leading-relaxed">
            Six stages, each with explicit, auditable state. The engine assumes jobs may run
            more than once and is built around idempotency and recovery.
          </p>
        </div>

        <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-3 border-t border-l border-border" data-stagger>
          {FLOW.map(([n, title, body]) => (
            <div key={n} className="border-b border-r border-border p-7 md:p-8">
              <div className="font-mono text-xs text-foreground-faint mb-5">{n}</div>
              <h3 className="font-serif text-xl mb-2.5">{title}</h3>
              <p className="text-sm text-foreground-muted leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="border-t border-border bg-surface-2">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-28">
          <div className="max-w-2xl" data-reveal>
            <div className="label-caps mb-4">Capabilities</div>
            <h2 className="font-serif text-3xl md:text-5xl leading-[1.05] tracking-tight">
              Everything a real orchestrator needs.
            </h2>
          </div>
          <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border border border-border" data-stagger>
            {CAPABILITIES.map((c) => (
              <div key={c.title} className="bg-surface p-7 md:p-8">
                <h3 className="font-serif text-xl mb-2.5">{c.title}</h3>
                <p className="text-sm text-foreground-muted leading-relaxed">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Concepts */}
      <section id="concepts" className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-28 grid lg:grid-cols-12 gap-10">
        <div className="lg:col-span-4" data-reveal>
          <div className="label-caps mb-4">Core Concepts</div>
          <h2 className="font-serif text-3xl md:text-4xl leading-tight tracking-tight">
            The vocabulary of the engine.
          </h2>
          <p className="text-foreground-muted mt-5 leading-relaxed text-sm">
            A small set of primitives composes into reliable, observable automation.
          </p>
        </div>
        <div className="lg:col-span-8 border-t border-border" data-stagger>
          {CONCEPTS.map(([term, def]) => (
            <div key={term} className="flex items-baseline gap-6 py-4 border-b border-border">
              <div className="w-28 shrink-0 font-mono text-sm">{term}</div>
              <div className="text-sm text-foreground-muted">{def}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-24 md:py-32 text-center" data-reveal>
          <h2 className="font-serif text-4xl md:text-6xl leading-[1.05] tracking-tight max-w-3xl mx-auto">
            Define a workflow. Watch it run.
          </h2>
          <p className="text-foreground-muted mt-6 max-w-xl mx-auto leading-relaxed">
            Connect your instance with an API key and start orchestrating distributed
            jobs with full visibility into every node transition.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center mt-10">
            <Link
              href="/login"
              className="inline-flex items-center justify-center h-11 px-7 bg-inverse text-inverse-foreground text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Connect Instance
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-11 px-7 bg-surface border border-border-strong text-foreground text-sm font-medium hover:bg-surface-hover transition-colors"
            >
              Open Dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Icons.Workflow className="w-4 h-4" />
            <span className="font-serif tracking-tight">EventFlow</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-foreground-muted">
            <a href="https://github.com/guptakaran20/EventFlow" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
            <Link href="/login" className="hover:text-foreground transition-colors">Connect</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
