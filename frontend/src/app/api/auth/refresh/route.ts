import { NextResponse } from "next/server";
import { refreshSession, AuthWorkflowError } from "@/lib/auth/service";

export async function POST() {
  try {
    await refreshSession();
    return NextResponse.json({ success: true });
  } catch (error: any) {
    const status = error instanceof AuthWorkflowError ? error.status : 500;
    return NextResponse.json(
      { message: error.message || "Internal server error" },
      { status }
    );
  }
}
