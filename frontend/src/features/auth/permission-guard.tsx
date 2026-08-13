"use client";

import React from "react";
import { useCurrentUser } from "./hooks/use-current-user";
import { UserRole } from "@/types";

interface PermissionGuardProps {
  allowed: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function PermissionGuard({
  allowed,
  children,
  fallback = null,
}: PermissionGuardProps) {
  const { data: user } = useCurrentUser();

  if (!user || !allowed.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
