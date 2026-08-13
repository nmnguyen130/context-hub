import { NextResponse } from "next/server";
import { logoutUser } from "@/lib/auth/service";

export async function POST() {
  await logoutUser();
  return new NextResponse(null, { status: 204 });
}
