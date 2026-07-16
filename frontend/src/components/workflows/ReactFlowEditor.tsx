import React, { useCallback, useRef, useState, useMemo } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Node as FlowNode,
  Edge as FlowEdge,
  NodeChange,
  EdgeChange,
  Connection,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { v4 as uuidv4 } from "uuid";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";

import { ExecutorNode, ExecutorNodeData } from "./nodes/ExecutorNode";
import { NodeConfigPanel } from "./NodeConfigPanel";
import { WorkflowDefinition } from "@/lib/types";
import { Icons } from "@/components/icons";

gsap.registerPlugin(useGSAP);

const nodeTypes = {
  executor: ExecutorNode,
};

const PALETTE: { type: string; label: string; accent: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { type: "http", label: "HTTP", accent: "#3b82f6", Icon: Icons.Globe },
  { type: "delay", label: "Delay", accent: "#f59e0b", Icon: Icons.Clock },
  { type: "condition", label: "Condition", accent: "#a855f7", Icon: Icons.GitBranch },
];

interface ReactFlowEditorProps {
  workflow: WorkflowDefinition;
  onChange: (workflow: WorkflowDefinition) => void;
}

export function ReactFlowEditor({ workflow, onChange }: ReactFlowEditorProps) {
  const initialNodes: FlowNode<ExecutorNodeData>[] = useMemo(() => {
    const nodesList = workflow.nodes || [];
    return nodesList.map((n, i) => ({
      id: n.id,
      type: "executor",
      position: { x: 280, y: i * 130 + 60 },
      data: {
        type: n.type,
        name: n.name,
        config: n.config || {},
      },
    }));
  }, [workflow.nodes]);

  const initialEdges: FlowEdge[] = useMemo(() => {
    const edgesList = workflow.edges || [];
    return edgesList.map((e) => ({
      id: `${e.from}-${e.to}`,
      source: e.from,
      target: e.to,
      label: e.condition || undefined,
      animated: true,
    }));
  }, [workflow.edges]);

  const [nodes, setNodes] = useState<FlowNode<ExecutorNodeData>[]>(initialNodes);
  const [edges, setEdges] = useState<FlowEdge[]>(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from(".react-flow__node", {
          opacity: 0,
          scale: 0.85,
          y: 12,
          duration: 0.5,
          stagger: 0.07,
          ease: "back.out(1.6)",
          clearProps: "transform,opacity",
        });
      });
      return () => mm.revert();
    },
    { scope: canvasRef }
  );

  const notifyChange = useCallback((newNodes: FlowNode<ExecutorNodeData>[], newEdges: FlowEdge[]) => {
    const updatedWorkflow: WorkflowDefinition = {
      ...workflow,
      nodes: newNodes.map((n) => ({
        id: n.id,
        type: n.data.type,
        name: n.data.name,
        config: n.data.config,
      })),
      edges: newEdges.map((e) => ({
        from: e.source,
        to: e.target,
        condition: e.label as string | undefined,
      })),
    };
    onChange(updatedWorkflow);
  }, [workflow, onChange]);

  const onNodesChange = useCallback(
    (changes: NodeChange<FlowNode<ExecutorNodeData>>[]) => {
      setNodes((nds) => {
        const next = applyNodeChanges(changes, nds);
        const structuralChange = changes.some(c => c.type === 'remove' || c.type === 'add');
        if (structuralChange) {
           notifyChange(next, edges);
        }
        return next;
      });
    },
    [edges, notifyChange]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<FlowEdge>[]) => {
      setEdges((eds) => {
        const next = applyEdgeChanges(changes, eds);
        notifyChange(nodes, next);
        return next;
      });
    },
    [nodes, notifyChange]
  );

  // Cycle detection via DFS
  const createsCycle = (source: string, target: string, allEdges: FlowEdge[]) => {
    if (source === target) return true;
    const adj: Record<string, string[]> = {};
    for (const e of allEdges) {
      if (!adj[e.source]) adj[e.source] = [];
      adj[e.source].push(e.target);
    }
    if (!adj[source]) adj[source] = [];
    adj[source].push(target);

    const visited = new Set<string>();
    const recStack = new Set<string>();

    const dfs = (nodeId: string): boolean => {
      if (recStack.has(nodeId)) return true;
      if (visited.has(nodeId)) return false;

      visited.add(nodeId);
      recStack.add(nodeId);

      const neighbors = adj[nodeId] || [];
      for (const n of neighbors) {
        if (dfs(n)) return true;
      }
      recStack.delete(nodeId);
      return false;
    };

    const nodeIds = new Set(allEdges.flatMap(e => [e.source, e.target]).concat([source, target]));
    for (const nodeId of nodeIds) {
      if (dfs(nodeId)) return true;
    }
    return false;
  };

  const onConnect = useCallback(
    (params: Connection) => {
      if (createsCycle(params.source, params.target, edges)) {
        alert("Cannot connect: creates a cycle in the DAG.");
        return;
      }
      setEdges((eds) => {
        const next = addEdge({ ...params, animated: true }, eds);
        notifyChange(nodes, next);
        return next;
      });
    },
    [edges, nodes, notifyChange]
  );

  const onNodeClick = useCallback((_: any, node: FlowNode) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleUpdateConfig = useCallback((nodeId: string, name: string, config: Record<string, any>) => {
    setNodes((nds) => {
      const next = nds.map((n) => {
        if (n.id === nodeId) {
          return { ...n, data: { ...n.data, name, config } };
        }
        return n;
      });
      notifyChange(next, edges);
      return next;
    });
  }, [edges, notifyChange]);

  const addNode = (type: string) => {
    const newNode: FlowNode<ExecutorNodeData> = {
      id: `node_${uuidv4().split('-')[0]}`,
      type: "executor",
      position: { x: Math.random() * 200 + 160, y: Math.random() * 200 + 120 },
      data: {
        type,
        name: `New ${type}`,
        config: type === "http" ? { method: "GET", url: "" } : type === "delay" ? { duration_seconds: 5 } : {},
      },
    };
    setNodes((nds) => {
      const next = nds.concat(newNode);
      notifyChange(next, edges);
      return next;
    });
  };

  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);

  return (
    <div className="relative w-full h-full min-h-0">
      <div ref={canvasRef} className="w-full h-full relative">
        <ReactFlow
          nodes={nodes.map(n => ({...n, selected: n.id === selectedNodeId}))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          colorMode="dark"
          fitView
          deleteKeyCode={["Delete", "Backspace"]}
          proOptions={{ hideAttribution: true }}
          className="dag-canvas"
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={22}
            size={1}
            className="opacity-60"
          />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeColor={() => "var(--foreground-muted)"}
            maskColor="color-mix(in srgb, var(--background) 78%, transparent)"
          />

          <Panel position="top-left" className="!m-4">
            <div className="dag-glass rounded-xl p-1.5 flex flex-col gap-1">
              <div className="label-caps px-2.5 pt-1.5 pb-1 !text-[10px]">Add Node</div>
              {PALETTE.map(({ type, label, accent, Icon }) => (
                <button
                  key={type}
                  onClick={() => addNode(type)}
                  className="group flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-sm text-foreground hover:bg-surface-hover transition-colors text-left"
                >
                  <span
                    className="flex items-center justify-center w-6 h-6 rounded-md shrink-0 transition-transform group-hover:scale-110"
                    style={{ background: `color-mix(in srgb, ${accent} 16%, transparent)`, color: accent }}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                  <span className="font-medium">{label}</span>
                  <Icons.Plus className="w-3.5 h-3.5 ml-auto text-foreground-faint opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
              <div className="px-2.5 pt-1.5 pb-1 mt-0.5 border-t border-border/60 text-[10px] text-foreground-faint">
                Select a node · press{" "}
                <kbd className="font-mono text-foreground-muted">Del</kbd> to remove
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>
      <NodeConfigPanel 
        selectedNode={selectedNode} 
        onUpdateConfig={handleUpdateConfig} 
        onClose={() => setSelectedNodeId(null)} 
      />
    </div>
  );
}
