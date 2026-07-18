"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

import { useRouter } from "next/navigation";

const COLLAPSE_KEY = "eventflow_sidebar_collapsed";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [navOpen, setNavOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("eventflow_auth_status")) {
      router.push("/login");
      return;
    }
    setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1");
  }, [router]);

  const toggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      return next;
    });
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar
        open={navOpen}
        onClose={() => setNavOpen(false)}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
      />
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
