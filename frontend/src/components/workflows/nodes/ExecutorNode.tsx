import React from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Icons } from "@/components/icons";
import { clsx } from "clsx";

export type ExecutorNodeData = {
  type: string;
  name: string;
  config: Record<string, any>;
  isInvalid?: boolean;
};

export type ExecutorFlowNode = Node<ExecutorNodeData, "executor">;

const TYPE_META: Record<
  string,
  { accent: string; label: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  http: { accent: "#3b82f6", label: "HTTP Request", Icon: Icons.Globe },
  delay: { accent: "#f59e0b", label: "Delay", Icon: Icons.Clock },
  condition: { accent: "#a855f7", label: "Condition", Icon: Icons.GitBranch },
  transform: { accent: "#10b981", label: "Transform", Icon: Icons.FileJson },
  webhook: { accent: "#ec4899", label: "Webhook", Icon: Icons.Webhook },
  notification: { accent: "#eab308", label: "Notification", Icon: Icons.Bell },
};

export function ExecutorNode({ data, selected }: NodeProps<ExecutorFlowNode>) {
  const meta = TYPE_META[data.type] ?? {
    accent: "var(--foreground-muted)",
    label: data.type,
    Icon: Icons.Settings,
  };
  const { Icon, accent } = meta;

  return (
    <div
      data-selected={selected ? "true" : "false"}
      className={clsx(
        "dag-node w-[260px] rounded-xl bg-surface/90 backdrop-blur-sm border flex flex-col overflow-hidden",
        selected ? "border-transparent" : "border-border",
        data.isInvalid && "!border-danger"
      )}
      style={{ ["--node-accent" as any]: data.isInvalid ? "var(--danger)" : accent }}
    >
      <Handle type="target" position={Position.Top} />

      <div className="flex items-center gap-2.5 px-3 py-2.5">
        <span
          className="flex items-center justify-center w-7 h-7 rounded-lg shrink-0"
          style={{
            background: `color-mix(in srgb, ${accent} 16%, transparent)`,
            color: accent,
          }}
        >
          <Icon className="w-3.5 h-3.5" />
        </span>
        <div className="min-w-0">
          <div className="font-medium text-[13px] text-foreground leading-tight truncate">
            {data.name || "Unnamed"}
          </div>
          <div
            className="text-[9px] font-semibold uppercase tracking-[0.12em] leading-tight"
            style={{ color: accent }}
          >
            {meta.label}
          </div>
        </div>
      </div>

      {(data.type === "http" && data.config?.method) ||
      (data.type === "delay" && data.config?.duration_seconds !== undefined) ||
      (data.type === "condition" && data.config?.expression) ? (
        <div className="px-3 pb-2.5 -mt-0.5">
          <div className="text-[10px] text-foreground-faint font-mono truncate border-t border-border/60 pt-2">
            {data.type === "http" && (
              <>
                <span className="text-foreground-muted">{data.config.method}</span>{" "}
                {data.config.url || "—"}
              </>
            )}
            {data.type === "delay" && <>wait {data.config.duration_seconds}s</>}
            {data.type === "condition" && data.config.expression}
          </div>
        </div>
      ) : null}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
