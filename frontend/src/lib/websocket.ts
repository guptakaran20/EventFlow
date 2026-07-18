import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ExecutionResponse, ExecutionLogResponse } from "./types";

export function useExecutionWebSocket(executionId: string) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!executionId) return;

    // Cookies are automatically sent via the browser
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = process.env.NEXT_PUBLIC_API_URL?.replace("http://", "").replace("https://", "")?.replace("/api/v1", "") || "localhost:8000";
    const wsUrl = `${protocol}//${host}/api/v1/ws/executions/${executionId}`;

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

        if (data.type === "execution_updated") {
          queryClient.setQueryData<ExecutionResponse>(["execution", executionId], (old) => {
            if (!old) return old;
            return { ...old, status: data.data.status };
          });
        }

        if (data.type === "node_updated") {
          queryClient.setQueryData<ExecutionResponse>(["execution", executionId], (old) => {
            if (!old) return old;
            const updatedNodes = old.node_executions.map(node =>
              node.node_id === data.data.node_id
                ? { ...node, status: data.data.status, attempt: data.data.attempt || node.attempt }
                : node
            );
            return { ...old, node_executions: updatedNodes };
          });
        }

        if (data.type === "execution_log") {
          queryClient.setQueryData<ExecutionLogResponse[]>(["execution_logs", executionId], (old) => {
            // we need to construct a pseudo log response object
            const logItem: ExecutionLogResponse = {
              log_id: Math.random().toString(36).substring(7),
              timestamp: data.timestamp,
              level: data.data.level,
              message: data.data.message,
              metadata: data.data.metadata || null
            };
            if (!old) return [logItem];
            return [...old, logItem];
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
