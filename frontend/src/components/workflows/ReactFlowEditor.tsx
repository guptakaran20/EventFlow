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
import dagre from "dagre";
import { toast } from "sonner";

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

const nodeWidth = 260;
const nodeHeight = 90;

const getLayoutedElements = (nodes: FlowNode[], edges: FlowEdge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: 'top',
      sourcePosition: 'bottom',
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: newNodes, edges };
};

export function ReactFlowEditor({ workflow, onChange }: ReactFlowEditorProps) {
  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    const nodesList = workflow.nodes || [];
    const seenIds = new Set<string>();
    const rawNodes: FlowNode<ExecutorNodeData>[] = nodesList.map((n) => {
      let id = n.id;
      if (!id || seenIds.has(id)) {
        id = `node_${Math.random().toString(36).substring(2, 9)}`;
      }
      seenIds.add(id);
      return {
        id,
        type: "executor",
        position: { x: 0, y: 0 },
        data: {
          type: n.type,
          name: n.name,
          config: n.config || {},
        },
      };
    });

    const edgesList = workflow.edges || [];
    const rawEdges: FlowEdge[] = edgesList
      .filter((e) => (e.from || (e as any).source) && (e.to || (e as any).target))
      .map((e) => {
        const source = e.from || (e as any).source;
        const target = e.to || (e as any).target;
        return {
          id: `${source}-${target}`,
          source,
          target,
          label: e.condition || undefined,
          animated: true,
        };
      });

    const { nodes: lNodes, edges: lEdges } = getLayoutedElements(rawNodes, rawEdges, 'TB');
    return { layoutedNodes: lNodes as FlowNode<ExecutorNodeData>[], layoutedEdges: lEdges };
  }, [workflow.nodes, workflow.edges]);

  const [nodes, setNodes] = useState<FlowNode<ExecutorNodeData>[]>(layoutedNodes);
  const [edges, setEdges] = useState<FlowEdge[]>(layoutedEdges);

  // Sync state when parent passes new structural workflow
  const [prevLayout, setPrevLayout] = useState({ layoutedNodes, layoutedEdges });
  if (layoutedNodes !== prevLayout.layoutedNodes || layoutedEdges !== prevLayout.layoutedEdges) {
    setPrevLayout({ layoutedNodes, layoutedEdges });
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

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
      const nextNodes = applyNodeChanges(changes, nodes);
      setNodes(nextNodes);
      const structuralChange = changes.some(c => c.type === 'remove' || c.type === 'add');
      if (structuralChange) {
         notifyChange(nextNodes, edges);
      }
    },
    [nodes, edges, notifyChange]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<FlowEdge>[]) => {
      const nextEdges = applyEdgeChanges(changes, edges);
      setEdges(nextEdges);
      notifyChange(nodes, nextEdges);
    },
    [nodes, edges, notifyChange]
  );

  const createsCycle = (source: string, target: string, allEdges: FlowEdge[]) => {
    if (source === target) return true;
    
    // We want to see if there's a path from `target` back to `source`.
    const adj: Record<string, string[]> = {};
    for (const e of allEdges) {
      if (!adj[e.source]) adj[e.source] = [];
      adj[e.source].push(e.target);
    }

    const visited = new Set<string>();

    const dfs = (nodeId: string): boolean => {
      if (nodeId === source) return true; // Reached the source! A cycle would be formed.
      if (visited.has(nodeId)) return false;
      
      visited.add(nodeId);

      const neighbors = adj[nodeId] || [];
      for (const n of neighbors) {
        if (dfs(n)) return true;
      }
      return false;
    };

    return dfs(target);
  };

  const onConnect = useCallback(
    (params: Connection) => {
      if (createsCycle(params.source, params.target, edges)) {
        toast.error("Cannot connect", {
          description: "This connection would create a cycle in the DAG.",
        });
        return;
      }
      const nextEdges = addEdge({ ...params, animated: true }, edges);
      setEdges(nextEdges);
      notifyChange(nodes, nextEdges);
    },
    [nodes, edges, notifyChange]
  );

  const onNodeClick = useCallback((_: any, node: FlowNode) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleUpdateConfig = useCallback((nodeId: string, name: string, config: Record<string, any>) => {
    const nextNodes = nodes.map((n) => {
      if (n.id === nodeId) {
        return { ...n, data: { ...n.data, name, config } };
      }
      return n;
    });
    setNodes(nextNodes);
    notifyChange(nextNodes, edges);
  }, [nodes, edges, notifyChange]);

  const addNode = (type: string) => {
    const newNodeId = `node_${uuidv4().split('-')[0]}`;
    const newNode: FlowNode<ExecutorNodeData> = {
      id: newNodeId,
      type: "executor",
      position: { x: 280, y: 120 }, // dagre will auto-layout this on next render
      data: {
        type,
        name: `New ${type}`,
        config: type === "http" ? { method: "GET", url: "" } : type === "delay" ? { duration_seconds: 5 } : {},
      },
    };
    
    let nextEdges = edges;
    const parentId = selectedNodeId || (nodes.length > 0 ? nodes[nodes.length - 1].id : null);
    
    if (parentId) {
      nextEdges = edges.concat({
        id: `${parentId}-${newNodeId}`,
        source: parentId,
        target: newNodeId,
        animated: true,
      });
      setEdges(nextEdges);
    }

    const nextNodes = nodes.concat(newNode);
    setNodes(nextNodes);
    setSelectedNodeId(newNodeId);
    notifyChange(nextNodes, nextEdges);
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
            <div className="dag-glass rounded-xl p-1.5 flex flex-col gap-1 w-40">
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
              <div className="px-2 pt-1.5 pb-1 mt-0.5 border-t border-border/60 text-[10px] text-foreground-faint text-center">
                Select · <kbd className="font-mono text-foreground-muted">Del</kbd> to delete
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
