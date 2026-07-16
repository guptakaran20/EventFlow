"use client";

import React from "react";
import Link from "next/link";
import { Icons } from "@/components/icons";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row overflow-hidden">
      {/* Left side content */}
      <div className="w-full md:w-[45%] flex flex-col justify-center p-8 md:p-24 lg:p-32 relative z-10 shrink-0 border-r border-border bg-background">
        <div className="flex items-center gap-3 mb-16">
          <Icons.Workflow className="w-6 h-6 text-brand" />
          <span className="font-medium tracking-tight">EventFlow</span>
        </div>
        
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-semibold tracking-tight text-foreground leading-[1.1] mb-6">
          Precision workflow orchestration.
        </h1>
        
        <p className="text-lg text-foreground-muted mb-12 max-w-md leading-relaxed">
          Engineered for reliability. Build, run, and observe distributed workflows without the noise.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4">
          <Link 
            href="/login" 
            className="inline-flex items-center justify-center bg-brand hover:bg-brand-hover text-white px-6 py-3 font-medium transition-colors"
          >
            Connect Instance
          </Link>
          <a 
            href="https://github.com/guptakaran20/EventFlow"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center bg-surface hover:bg-surface-hover border border-border text-foreground px-6 py-3 font-medium transition-colors"
          >
            Documentation
          </a>
        </div>
      </div>
      
      {/* Right side illustration */}
      <div className="flex-1 bg-surface relative overflow-hidden flex items-center justify-center min-h-[50vh]">
        {/* Technical abstract illustration */}
        <div className="absolute inset-0 opacity-80 pointer-events-none">
          <svg className="w-full h-full text-border" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor">
            {/* Background grid */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" stroke="currentColor" strokeWidth="0.5" strokeOpacity="0.3"/>
            </pattern>
            <rect width="100%" height="100%" fill="url(#grid)" />
            
            {/* Blueprint geometry */}
            <g strokeWidth="1" strokeOpacity="0.7">
              {/* Central orchestration node */}
              <circle cx="500" cy="500" r="120" strokeDasharray="4 4" />
              <circle cx="500" cy="500" r="80" />
              
              {/* Branching paths */}
              <path d="M 500 420 L 500 200 L 300 200" />
              <path d="M 500 580 L 500 800 L 700 800" />
              <path d="M 580 500 L 800 500 L 800 300" />
              <path d="M 420 500 L 200 500 L 200 700" />
              
              {/* Worker nodes */}
              <rect x="260" y="180" width="40" height="40" />
              <rect x="700" y="780" width="40" height="40" />
              <rect x="780" y="260" width="40" height="40" />
              <rect x="180" y="700" width="40" height="40" />
              
              {/* Connections between workers */}
              <path d="M 300 180 L 780 180 L 780 260" strokeDasharray="2 4" />
              <path d="M 220 740 L 700 740 L 700 820" strokeDasharray="2 4" />
              
              {/* Active data flow visualization */}
              <circle cx="500" cy="300" r="4" className="text-brand fill-brand animate-pulse" />
              <circle cx="650" cy="500" r="4" className="text-brand fill-brand animate-pulse" style={{ animationDelay: '1s' }} />
              <circle cx="350" cy="500" r="4" className="text-brand fill-brand animate-pulse" style={{ animationDelay: '0.5s' }} />
              <circle cx="500" cy="650" r="4" className="text-brand fill-brand animate-pulse" style={{ animationDelay: '1.5s' }} />
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}
