import { getAuthTokens, setAuthCookies, clearAuthCookies } from "./session";
import { User } from "@/types";

const BACKEND_URL = process.env.INTERNAL_API_URL || "http://backend:8000/api/v1";

export class AuthWorkflowError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "AuthWorkflowError";
    this.status = status;
  }
}

let activeRefreshPromise: Promise<boolean> | null = null;

function normalizeErrorMessage(status: number, rawDetail?: string): string {
  if (status === 401) return rawDetail || "Invalid email or password.";
  if (status === 403) return "Access denied. You do not have permission for this tenant.";
  if (status === 404) return "Requested authentication resource not found.";
  if (status >= 500) return "Authentication service unavailable. Please try again later.";
  return rawDetail || "An authentication error occurred.";
}

/**
 * Internal helper: Resolves a valid access token.
 * Reads accessToken from cookie. If missing, attempts to refresh token pair.
 */
async function getValidAccessToken(): Promise<string> {
  const { accessToken, refreshToken } = await getAuthTokens();

  if (accessToken) {
    return accessToken;
  }

  if (!refreshToken) {
    throw new AuthWorkflowError(401, "Unauthenticated");
  }

  // Attempt refresh token exchange
  await refreshSession();
  const { accessToken: newAccessToken } = await getAuthTokens();

  if (!newAccessToken) {
    throw new AuthWorkflowError(401, "Failed to obtain valid session token");
  }

  return newAccessToken;
}

export async function loginUser(credentials: {
  tenant_slug: string;
  email: string;
  password: string;
}): Promise<User> {
  const { tenant_slug, email, password } = credentials;

  // 1. Authenticate against FastAPI backend
  const loginRes = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-Slug": tenant_slug,
    },
    body: JSON.stringify({ email, password }),
  });

  if (!loginRes.ok) {
    const errorData = await loginRes.json().catch(() => ({}));
    throw new AuthWorkflowError(
      loginRes.status,
      normalizeErrorMessage(loginRes.status, errorData.detail)
    );
  }

  const { access_token, refresh_token } = await loginRes.json();

  // 2. Fetch User Profile BEFORE setting cookies (Transactional purity)
  const meRes = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });

  if (!meRes.ok) {
    throw new AuthWorkflowError(
      meRes.status,
      normalizeErrorMessage(meRes.status, "Failed to fetch user profile after authentication.")
    );
  }

  const user = await meRes.json();

  // 3. Set HTTPOnly cookies ONLY upon full workflow success
  await setAuthCookies({ access_token, refresh_token });

  return user;
}

export async function refreshSession(): Promise<boolean> {
  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  activeRefreshPromise = (async () => {
    try {
      const { refreshToken } = await getAuthTokens();

      if (!refreshToken) {
        throw new AuthWorkflowError(401, "No refresh token available");
      }

      const refreshRes = await fetch(`${BACKEND_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!refreshRes.ok) {
        await clearAuthCookies();
        const errorData = await refreshRes.json().catch(() => ({}));
        throw new AuthWorkflowError(
          401,
          normalizeErrorMessage(401, errorData.detail || "Refresh token expired or revoked")
        );
      }

      const tokenData = await refreshRes.json();
      await setAuthCookies(tokenData);
      return true;
    } finally {
      activeRefreshPromise = null;
    }
  })();

  return activeRefreshPromise;
}

export async function getCurrentUser(): Promise<User> {
  const accessToken = await getValidAccessToken();

  const meRes = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!meRes.ok) {
    // If access token was rejected by backend (401), attempt 1-time refresh + retry
    if (meRes.status === 401) {
      try {
        await refreshSession();
        const { accessToken: freshAccessToken } = await getAuthTokens();
        if (freshAccessToken) {
          const retryRes = await fetch(`${BACKEND_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${freshAccessToken}` },
          });

          if (retryRes.ok) {
            return await retryRes.json();
          }
        }
      } catch {
        // Refresh failed
      }

      await clearAuthCookies();
      throw new AuthWorkflowError(401, "Session expired. Please sign in again.");
    }

    throw new AuthWorkflowError(
      meRes.status,
      normalizeErrorMessage(meRes.status, "Failed to fetch user profile")
    );
  }

  return await meRes.json();
}

export async function logoutUser(): Promise<void> {
  const { accessToken, refreshToken } = await getAuthTokens();

  if (refreshToken) {
    await fetch(`${BACKEND_URL}/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }

  await clearAuthCookies();
}
