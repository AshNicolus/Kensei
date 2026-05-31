import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { jobsApi } from "@/modules/automl/api/automl-api";
import { StatusBadge } from "@/modules/automl/components/StatusBadge";
import { timeAgo } from "@/shared/lib/utils";

export function JobsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: jobsApi.list,
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Every training run you've started.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : !data || data.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No training runs yet.
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-muted-foreground bg-card/50">
              <tr className="border-b border-border/60 text-xs">
                <th className="text-left px-4 py-3 font-medium">Job</th>
                <th className="text-left px-4 py-3 font-medium">Target</th>
                <th className="text-left px-4 py-3 font-medium">Task</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.map((j) => (
                <tr
                  key={j.id}
                  className="border-b border-border/30 hover:bg-accent/40 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/automl/jobs/${j.id}`}
                      className="font-mono text-primary hover:underline"
                    >
                      #{j.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{j.target}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {j.task_type}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={j.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                    {timeAgo(j.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
