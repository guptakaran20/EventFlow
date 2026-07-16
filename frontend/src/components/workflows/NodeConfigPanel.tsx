import React from "react";
import { Node as FlowNode } from "@xyflow/react";
import { ExecutorNodeData } from "./nodes/ExecutorNode";
import { Icons } from "@/components/icons";

interface NodeConfigPanelProps {
  selectedNode: FlowNode<ExecutorNodeData> | null;
  onUpdateConfig: (nodeId: string, name: string, config: Record<string, any>) => void;
}

export function NodeConfigPanel({ selectedNode, onUpdateConfig }: NodeConfigPanelProps) {
  if (!selectedNode) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center border-l border-border bg-surface text-foreground-faint">
        <Icons.MousePointer2 className="w-8 h-8 mb-4 opacity-50" />
        <p className="text-sm">Select a node to configure its properties</p>
      </div>
    );
  }

  const { id, data } = selectedNode;
  const { name, type, config } = data;

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateConfig(id, e.target.value, config);
  };

  const handleConfigChange = (key: string, value: any) => {
    onUpdateConfig(id, name, { ...config, [key]: value });
  };

  return (
    <div className="flex-1 flex flex-col border-l border-border bg-surface overflow-hidden w-80 shrink-0">
      <div className="p-4 border-b border-border bg-surface-2 flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-surface border border-border flex items-center justify-center shrink-0">
          <Icons.Settings className="w-4 h-4 text-foreground" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-foreground truncate">{name || "Unnamed Node"}</div>
          <div className="text-xs text-foreground-muted uppercase tracking-wider">{type}</div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-6">
        <div className="space-y-2">
          <label className="text-xs font-medium text-foreground">Node Name</label>
          <input
            type="text"
            value={name}
            onChange={handleNameChange}
            className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            placeholder="e.g. Fetch Users"
          />
        </div>

        <div className="space-y-4">
          <h4 className="text-xs font-medium text-foreground uppercase tracking-wider pb-2 border-b border-border">
            Configuration
          </h4>
          
          {type === "http" && (
            <>
              <div className="space-y-2">
                <label className="text-xs text-foreground-muted">Method</label>
                <select
                  value={config.method || "GET"}
                  onChange={(e) => handleConfigChange("method", e.target.value)}
                  className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                  <option value="PATCH">PATCH</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-foreground-muted">URL</label>
                <input
                  type="text"
                  value={config.url || ""}
                  onChange={(e) => handleConfigChange("url", e.target.value)}
                  className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                  placeholder="https://api.example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-foreground-muted">Headers (JSON)</label>
                <textarea
                  value={typeof config.headers === 'object' ? JSON.stringify(config.headers, null, 2) : config.headers || ""}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      handleConfigChange("headers", parsed);
                    } catch {
                      handleConfigChange("headers", e.target.value); // Wait for valid json
                    }
                  }}
                  className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono h-24"
                  placeholder='{"Authorization": "Bearer token"}'
                />
              </div>
            </>
          )}

          {type === "delay" && (
            <div className="space-y-2">
              <label className="text-xs text-foreground-muted">Duration (Seconds)</label>
              <input
                type="number"
                min="0"
                value={config.duration_seconds || 0}
                onChange={(e) => handleConfigChange("duration_seconds", parseInt(e.target.value, 10))}
                className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
              />
            </div>
          )}

          {type === "condition" && (
            <div className="space-y-2">
              <label className="text-xs text-foreground-muted">Expression (JMESPath/JS-like)</label>
              <input
                type="text"
                value={config.expression || ""}
                onChange={(e) => handleConfigChange("expression", e.target.value)}
                className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono"
                placeholder="status == 'success'"
              />
            </div>
          )}

          {/* Fallback for other or unknown configs */}
          {type !== "http" && type !== "delay" && type !== "condition" && (
            <div className="space-y-2">
              <label className="text-xs text-foreground-muted">Config (JSON)</label>
              <textarea
                value={JSON.stringify(config, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value);
                    onUpdateConfig(id, name, parsed);
                  } catch {
                    // ignore invalid
                  }
                }}
                className="w-full bg-surface-2 border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground font-mono h-48"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
