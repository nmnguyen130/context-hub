import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;
  const hasSession = Boolean(accessToken || refreshToken);

  // 1. Protected application routes
  const protectedPaths = ["/dashboard", "/chat", "/workspaces", "/settings"];
  const isProtected = protectedPaths.some((path) => pathname.startsWith(path));

  if (isProtected) {
    if (!hasSession) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // 2. Redirect authenticated users away from auth pages to /dashboard
  if (pathname === "/login" || pathname === "/register") {
    if (hasSession) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  // 3. Inject Bearer token into request headers for backend rewrites (/api/v1/*)
  if (pathname.startsWith("/api/v1")) {
    if (accessToken) {
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set("authorization", `Bearer ${accessToken}`);
      return NextResponse.next({
        request: {
          headers: requestHeaders,
        },
      });
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/chat/:path*",
    "/workspaces/:path*",
    "/settings/:path*",
    "/login",
    "/register",
    "/api/v1/:path*",
  ],
};
