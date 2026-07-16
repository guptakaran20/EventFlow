"use client";

import React, { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar onMenu={() => setNavOpen(true)} />
        <main className="flex-1 overflow-auto bg-background">
          <div className="max-w-6xl mx-auto px-5 md:px-8 lg:px-10 py-8 md:py-10 h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
