import { Badge } from "@/shared/components/ui/badge";
import type { JobStatus } from "@/modules/automl/api/types";

const MAP: Record<JobStatus, { variant: React.ComponentProps<typeof Badge>["variant"]; label: string }> = {
  pending: { variant: "muted", label: "pending" },
  running: { variant: "warning", label: "running" },
  succeeded: { variant: "success", label: "succeeded" },
  failed: { variant: "destructive", label: "failed" },
  cancelled: { variant: "muted", label: "cancelled" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const m = MAP[status] ?? { variant: "muted" as const, label: status };
  return <Badge variant={m.variant}>{m.label}</Badge>;
}
