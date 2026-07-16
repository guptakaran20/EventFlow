import React, { useCallback, useEffect, useState, useMemo } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Node as FlowNode,
  Edge as FlowEdge,
  NodeChange,
  EdgeChange,
  Connection,
  Panel,
  ColorMode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { v4 as uuidv4 } from "uuid";

import { ExecutorNode, ExecutorNodeData } from "./nodes/ExecutorNode";
import { NodeConfigPanel } from "./NodeConfigPanel";
import { WorkflowDefinition, Node, Edge } from "@/lib/types";
import { Icons } from "@/components/icons";
import { Button } from "@/components/ui";

const nodeTypes = {
  executor: ExecutorNode,
};

interface ReactFlowEditorProps {
  workflow: WorkflowDefinition;
  onChange: (workflow: WorkflowDefinition) => void;
}

export function ReactFlowEditor({ workflow, onChange }: ReactFlowEditorProps) {
  // Convert WorkflowDefinition to ReactFlow format on mount/props change
  const initialNodes: FlowNode<ExecutorNodeData>[] = useMemo(() => {
    const nodesList = workflow.nodes || [];
    return nodesList.map((n, i) => ({
      id: n.id,
      type: "executor",
      // Simple auto-layout if they all spawn at 0,0. In a real app we'd save positions in the node config metadata.
      position: { x: 250, y: i * 100 + 50 },
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
    }));
  }, [workflow.edges]);

  const [nodes, setNodes] = useState<FlowNode<ExecutorNodeData>[]>(initialNodes);
  const [edges, setEdges] = useState<FlowEdge[]>(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Sync back to workflow definition
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
        // Only notify if something other than selection/position changed?
        // Actually, position isn't saved in MVP, so we don't strictly need to notify on drag, 
        // but removing nodes should trigger notify.
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
    // Add the prospective edge
    if (!adj[source]) adj[source] = [];
    adj[source].push(target);

    // Check for cycles
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

    // Check from all nodes
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
        const next = addEdge(params, eds);
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
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
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
    <div className="flex w-full h-full min-h-0 bg-surface">
      <div className="flex-1 h-full relative">
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
          className="bg-surface-2"
        >
          <Background gap={16} size={1} />
          <Controls />
          
          <Panel position="top-left" className="bg-surface border border-border rounded shadow-sm p-2 flex gap-2">
            <Button variant="outline" size="sm" onClick={() => addNode("http")}>
              <Icons.Globe className="w-3.5 h-3.5 mr-1 text-blue-500" /> HTTP
            </Button>
            <Button variant="outline" size="sm" onClick={() => addNode("delay")}>
              <Icons.Clock className="w-3.5 h-3.5 mr-1 text-amber-500" /> Delay
            </Button>
            <Button variant="outline" size="sm" onClick={() => addNode("condition")}>
              <Icons.GitBranch className="w-3.5 h-3.5 mr-1 text-purple-500" /> Condition
            </Button>
          </Panel>
        </ReactFlow>
      </div>
      
      <NodeConfigPanel selectedNode={selectedNode} onUpdateConfig={handleUpdateConfig} />
    </div>
  );
}
