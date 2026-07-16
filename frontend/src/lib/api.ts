const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public message: string, public data?: any) {
    super(message);
    this.name = "ApiError";
  }
}

function getAuthHeader() {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("eventflow_api_key") : null;
  if (!apiKey) {
    throw new Error("No API key found in localStorage");
  }
  return { "X-EventFlow-API-Key": apiKey };
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  let data;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, data?.detail || response.statusText, data);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body: any, options?: RequestInit) =>
    request<T>(endpoint, { ...options, method: "POST", body: JSON.stringify(body) }),
  put: <T>(endpoint: string, body: any, options?: RequestInit) =>
    request<T>(endpoint, { ...options, method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: "DELETE" }),
  
  // Custom non-v1 endpoint for verification
  verifyAuth: async () => {
    const apiKey = typeof window !== "undefined" ? localStorage.getItem("eventflow_api_key") : null;
    const url = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace('/api/v1', '') + "/auth/verify";
    
    const response = await fetch(url, {
      headers: { "X-EventFlow-API-Key": apiKey || "" }
    });
    return response.ok;
  }
};
