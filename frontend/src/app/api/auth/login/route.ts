import { NextResponse } from "next/server";
import { loginUser, AuthWorkflowError } from "@/lib/auth/service";

export async function POST(request: Request) {
  try {
    const { tenant_slug, email, password } = await request.json();

    if (!email || !password || !tenant_slug) {
      return NextResponse.json(
        { message: "Missing required login credentials" },
        { status: 400 }
      );
    }

    const user = await loginUser({ tenant_slug, email, password });
    return NextResponse.json({ user });
  } catch (error: any) {
    const status = error instanceof AuthWorkflowError ? error.status : 500;
    return NextResponse.json(
      { message: error.message || "Internal server error" },
      { status }
    );
  }
}
