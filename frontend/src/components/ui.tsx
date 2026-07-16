"use client";

import React from "react";
import { twMerge } from "tailwind-merge";
import clsx from "clsx";

export const cn = (...inputs: any[]) => twMerge(clsx(inputs));

/* ---------------- Button ---------------- */

type ButtonVariant = "primary" | "ghost" | "outline" | "danger";

export function Button({
  variant = "outline",
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  const base =
    "inline-flex items-center justify-center gap-2 px-3.5 h-9 text-sm font-medium transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed select-none";
  const variants: Record<ButtonVariant, string> = {
    primary:
      "bg-inverse text-inverse-foreground hover:opacity-90 cursor-pointer",
    outline:
      "border border-border-strong text-foreground bg-surface hover:bg-surface-hover cursor-pointer",
    ghost:
      "text-foreground-muted hover:text-foreground hover:bg-surface-hover cursor-pointer",
    danger:
      "border border-danger-border text-danger bg-danger-soft hover:opacity-90 cursor-pointer",
  };
  return (
    <button className={cn(base, variants[variant], className)} {...props}>
      {children}
    </button>
  );
}

/* ---------------- Link-styled button ---------------- */

export function LinkButton({
  variant = "primary",
  className,
  children,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { variant?: ButtonVariant }) {
  const base =
    "inline-flex items-center justify-center gap-2 px-3.5 h-9 text-sm font-medium transition-colors duration-150 select-none cursor-pointer";
  const variants: Record<ButtonVariant, string> = {
    primary: "bg-inverse text-inverse-foreground hover:opacity-90",
    outline:
      "border border-border-strong text-foreground bg-surface hover:bg-surface-hover",
    ghost: "text-foreground-muted hover:text-foreground hover:bg-surface-hover",
    danger:
      "border border-danger-border text-danger bg-danger-soft hover:opacity-90",
  };
  return (
    <a className={cn(base, variants[variant], className)} {...props}>
      {children}
    </a>
  );
}

/* ---------------- PageHeader ---------------- */

export function PageHeader({
  title,
  description,
  actions,
  danger,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1
          className={cn(
            "font-serif text-3xl md:text-4xl leading-[1.1] tracking-tight",
            danger ? "text-danger" : "text-foreground"
          )}
        >
          {title}
        </h1>
        {description && (
          <p className="text-sm text-foreground-muted mt-2 max-w-xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ---------------- Panel ---------------- */

export function Panel({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("border border-border bg-surface", className)}>
      {children}
    </div>
  );
}

export function PanelHeader({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "px-4 h-11 flex items-center justify-between border-b border-border bg-surface-2",
        className
      )}
    >
      {children}
    </div>
  );
}

/* ---------------- Badge / status pill ---------------- */

export function Badge({
  children,
  danger,
  className,
}: {
  children: React.ReactNode;
  danger?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 h-6 px-2 text-[11px] font-medium font-mono uppercase tracking-wide border",
        danger
          ? "text-danger border-danger-border bg-danger-soft"
          : "text-foreground-muted border-border bg-surface-2",
        className
      )}
    >
      {children}
    </span>
  );
}

/* ---------------- EmptyState ---------------- */

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border border-border bg-surface px-6 py-16 flex flex-col items-center justify-center text-center">
      {icon && <div className="text-foreground-faint mb-5 opacity-60">{icon}</div>}
      <h3 className="font-serif text-xl text-foreground">{title}</h3>
      {description && (
        <p className="text-sm text-foreground-muted mt-2 max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/* ---------------- Table shells ---------------- */

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-border bg-surface overflow-x-auto">
      <table className="w-full text-left text-sm border-collapse">{children}</table>
    </div>
  );
}

export function Th({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "px-4 h-10 font-medium text-[11px] uppercase tracking-wider text-foreground-faint bg-surface-2 border-b border-border whitespace-nowrap",
        className
      )}
    >
      {children}
    </th>
  );
}
