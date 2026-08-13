export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface RequestOptions extends RequestInit {
  tenantSlug?: string | null;
  _isRetry?: boolean;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { tenantSlug, headers: customHeaders, _isRetry, ...restOptions } = options;

  const headers: Record<string, string> = {
    ...(customHeaders as Record<string, string>),
  };

  if (!(restOptions.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (tenantSlug) {
    headers["X-Tenant-Slug"] = tenantSlug;
  }

  const config: RequestInit = {
    ...restOptions,
    headers,
    credentials: "include", // Send HTTPOnly cookies automatically
  };

  // Relative endpoints: /api/auth/* (BFF) or /api/v1/* (FastAPI via Next.js rewrite)
  const url = endpoint.startsWith("/api/") ? endpoint : `/api/v1${endpoint}`;

  const response = await fetch(url, config);

  if (!response.ok) {
    // Attempt automatic silent refresh once if 401 on non-auth endpoints
    if (response.status === 401 && !_isRetry && !endpoint.includes("/auth/")) {
      try {
        const refreshRes = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (refreshRes.ok) {
          return apiClient<T>(endpoint, { ...options, _isRetry: true });
        }
      } catch {
        // Fall through to error parsing
      }
    }

    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }

    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : errorData.detail?.[0]?.msg || errorData.message || "An unexpected error occurred.";

    throw new ApiError(response.status, message, errorData);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json();
}
