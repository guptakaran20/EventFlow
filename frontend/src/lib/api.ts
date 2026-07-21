const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public message: string, public data?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

function getAuthHeader() {
  return {};
}

async function refreshAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include"
    });
    
    if (response.ok) {
      return true;
    }
  } catch {
    // Ignore refresh errors
  }
  return false;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  let response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers,
  });

  // Auto-refresh token on 401
  if (response.status === 401 && endpoint !== "/auth/token" && endpoint !== "/auth/refresh") {
    const success = await refreshAccessToken();
    if (success) {
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        credentials: "include",
        headers,
      });
    } else {
      // If refresh fails, log out
      localStorage.removeItem("eventflow_auth_status");
      window.location.href = "/login";
    }
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    let errorMsg = response.statusText;
    let details = data;

    if (data?.error) {
      errorMsg = data.error.message || errorMsg;
      if (Array.isArray(data.error.details)) {
        errorMsg += ": " + data.error.details.map((e: { loc?: string[]; msg: string }) => `${e.loc?.join('.') || 'unknown'}: ${e.msg}`).join(', ');
      }
      details = data.error.details || data.error;
    } else if (data?.detail) {
      if (typeof data.detail === "string") {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((e: { loc?: string[]; msg: string }) => `${e.loc?.join('.') || 'unknown'}: ${e.msg}`).join(', ');
      }
      details = data.detail;
    }

    throw new ApiError(response.status, errorMsg, details);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    request<T>(endpoint, { ...options, method: "POST", body: JSON.stringify(body) }),
  put: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    request<T>(endpoint, { ...options, method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: "DELETE" }),
  
  // Authenticate and get JWT
  login: async (apiKey: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ api_key: apiKey })
    });
    
    if (response.ok) {
      localStorage.setItem("eventflow_auth_status", "1");
      return true;
    }
    return false;
  },

  logout: async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include"
      });
    } catch {}
    localStorage.removeItem("eventflow_auth_status");
    window.location.href = "/login";
  },

  // Get current user info
  me: async () => request<{ raw_key: string; key_type: string }>("/auth/me"),
  
  createDemoKey: async () => {
    const response = await fetch(`${API_BASE_URL}/auth/demo-key`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      throw new Error("Failed to create demo API key");
    }
    const data = await response.json();
    return data.raw_key as string;
  }
};
