const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public message: string, public data?: any) {
    super(message);
    this.name = "ApiError";
  }
}

function getAuthHeader() {
  const token = typeof window !== "undefined" ? localStorage.getItem("eventflow_jwt") : null;
  if (!token) {
    throw new Error("No JWT token found in localStorage");
  }
  return { "Authorization": `Bearer ${token}` };
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = typeof window !== "undefined" ? localStorage.getItem("eventflow_refresh") : null;
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem("eventflow_jwt", data.access_token);
      localStorage.setItem("eventflow_refresh", data.refresh_token);
      return data.access_token;
    }
  } catch (e) {
    // Ignore refresh errors
  }
  return null;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  let response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // Auto-refresh token on 401
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });
    } else {
      // If refresh fails, log out
      localStorage.removeItem("eventflow_jwt");
      localStorage.removeItem("eventflow_refresh");
      window.location.href = "/login";
    }
  }

  let data;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  if (!response.ok) {
    let errorMsg = response.statusText;
    let details = data;

    if (data?.error) {
      errorMsg = data.error.message || errorMsg;
      if (Array.isArray(data.error.details)) {
        errorMsg += ": " + data.error.details.map((e: any) => `${e.loc?.join('.') || 'unknown'}: ${e.msg}`).join(', ');
      }
      details = data.error.details || data.error;
    } else if (data?.detail) {
      if (typeof data.detail === "string") {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((e: any) => `${e.loc?.join('.') || 'unknown'}: ${e.msg}`).join(', ');
      }
      details = data.detail;
    }

    throw new ApiError(response.status, errorMsg, details);
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
  
  // Authenticate and get JWT
  login: async (apiKey: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem("eventflow_jwt", data.access_token);
      localStorage.setItem("eventflow_refresh", data.refresh_token);
      return true;
    }
    return false;
  },

  // Get current user info
  me: async () => request<{ raw_key: string; key_type: string }>("/auth/me")
};
