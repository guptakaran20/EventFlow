import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { Icons } from "@/components/icons";
import { clsx } from "clsx";

export type ExecutorNodeData = {
  type: string;
  name: string;
  config: Record<string, any>;
  isInvalid?: boolean;
};

export function ExecutorNode({ data, selected }: NodeProps<ExecutorNodeData>) {
  // Select an icon based on the executor type
  const renderIcon = () => {
    switch (data.type) {
      case "http":
        return <Icons.Globe className="w-4 h-4 text-blue-500" />;
      case "delay":
        return <Icons.Clock className="w-4 h-4 text-amber-500" />;
      case "condition":
        return <Icons.GitBranch className="w-4 h-4 text-purple-500" />;
      case "transform":
        return <Icons.FileJson className="w-4 h-4 text-emerald-500" />;
      case "webhook":
        return <Icons.Webhook className="w-4 h-4 text-pink-500" />;
      case "notification":
        return <Icons.Bell className="w-4 h-4 text-yellow-500" />;
      default:
        return <Icons.Settings className="w-4 h-4 text-foreground-muted" />;
    }
  };

  return (
    <div
      className={clsx(
        "min-w-[160px] bg-surface rounded-md border flex flex-col overflow-hidden shadow-sm transition-all",
        selected ? "border-primary ring-1 ring-primary/20" : "border-border",
        data.isInvalid ? "border-danger ring-1 ring-danger/20" : ""
      )}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-foreground-muted !border-none" />
      
      <div className="flex items-center gap-2 p-2 border-b border-border bg-surface-2">
        {renderIcon()}
        <span className="font-medium text-sm text-foreground">{data.name || "Unnamed"}</span>
      </div>
      
      <div className="p-2 text-xs text-foreground-faint bg-surface flex flex-col gap-1">
        <div className="uppercase tracking-wider font-semibold text-[10px] text-foreground-muted">
          {data.type}
        </div>
        
        {/* Quick summary of config */}
        {data.type === "http" && data.config?.method && (
          <div className="truncate font-mono">
            {data.config.method} {data.config.url}
          </div>
        )}
        {data.type === "delay" && data.config?.duration_seconds !== undefined && (
          <div>Wait {data.config.duration_seconds}s</div>
        )}
        {data.type === "condition" && data.config?.expression && (
          <div className="truncate font-mono">{data.config.expression}</div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-foreground-muted !border-none" />
    </div>
  );
}
