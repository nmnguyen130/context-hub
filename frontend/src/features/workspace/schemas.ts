import { z } from "zod";

export const workspaceSchema = z.object({
  name: z.string().min(2, "Workspace name must be at least 2 characters"),
  slug: z.string().optional(),
  description: z.string().optional(),
});

export type WorkspaceFormValues = z.infer<typeof workspaceSchema>;
