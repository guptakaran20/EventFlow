import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ExecutionResponse, ExecutionLogResponse } from "./types";

export function useExecutionWebSocket(executionId: string) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!executionId) return;

    const apiKey = localStorage.getItem("eventflow_api_key");
    if (!apiKey) return;

    // Use ws:// or wss:// based on current protocol
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = process.env.NEXT_PUBLIC_API_URL?.replace("http://", "").replace("https://", "")?.replace("/api/v1", "") || "localhost:8000";
    const wsUrl = `${protocol}//${host}/api/v1/ws/executions/${executionId}?api_key=${apiKey}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "execution.started" || data.type === "execution.completed" || data.type === "execution.failed") {
          queryClient.setQueryData<ExecutionResponse>(["execution", executionId], (old) => {
            if (!old) return old;
            return { ...old, status: data.payload.status };
          });
        }
        
        if (data.type === "node.queued" || data.type === "node.started" || data.type === "node.completed" || data.type === "node.failed" || data.type === "node.dead_lettered") {
          queryClient.setQueryData<ExecutionResponse>(["execution", executionId], (old) => {
            if (!old) return old;
            const updatedNodes = old.node_executions.map(node => 
              node.node_id === data.payload.node_id 
                ? { ...node, status: data.payload.status, attempt: data.payload.attempt || node.attempt } 
                : node
            );
            return { ...old, node_executions: updatedNodes };
          });
        }
        
        if (data.type === "log.appended") {
          queryClient.setQueryData<ExecutionLogResponse[]>(["execution_logs", executionId], (old) => {
            if (!old) return [data.payload];
            return [...old, data.payload];
          });
        }
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [executionId, queryClient]);

  return { isConnected };
}
