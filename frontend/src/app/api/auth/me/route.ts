import { NextResponse } from "next/server";
import { getCurrentUser, AuthWorkflowError } from "@/lib/auth/service";

export async function GET() {
  try {
    const user = await getCurrentUser();
    return NextResponse.json(user);
  } catch (error: any) {
    const status = error instanceof AuthWorkflowError ? error.status : 500;
    return NextResponse.json(
      { message: error.message || "Internal server error" },
      { status }
    );
  }
}
