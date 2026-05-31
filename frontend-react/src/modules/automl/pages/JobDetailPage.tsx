import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Button } from "@/shared/components/ui/button";
import { jobsApi } from "@/modules/automl/api/automl-api";
import { StatusBadge } from "@/modules/automl/components/StatusBadge";
import { FeatureImportanceChart } from "@/modules/automl/components/FeatureImportanceChart";
import { formatScore, timeAgo } from "@/shared/lib/utils";

export function JobDetailPage() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => jobsApi.get(id),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "running" || status === "pending" ? 2000 : false;
    },
    enabled: !isNaN(id),
  });
  const models = useQuery({
    queryKey: ["job-models", id],
    queryFn: () => jobsApi.models(id),
    enabled: !isNaN(id) && job.data?.status === "succeeded",
  });

  if (job.isLoading) return <Skeleton className="h-40" />;
  if (!job.data) return <p>Job not found.</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm" className="-ml-3">
          <Link to="/automl/jobs">
            <ArrowLeft className="size-4" />
            All jobs
          </Link>
        </Button>
        <StatusBadge status={job.data.status} />
      </div>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Job <span className="font-mono text-muted-foreground">#{job.data.id}</span>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Target <span className="font-mono text-foreground">{job.data.target}</span>{" "}
          · {job.data.task_type} · created {timeAgo(job.data.created_at)}
        </p>
        {job.data.message && (
          <p className="text-xs text-muted-foreground mt-2 font-mono">
            {job.data.message}
          </p>
        )}
      </div>

      {models.data && models.data.length > 0 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Candidate models</CardTitle>
              <CardDescription>
                Sorted by{" "}
                <span className="font-mono">
                  {models.data[0].primary_metric}
                </span>{" "}
                — best at the top.
              </CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/60 text-xs">
                    <th className="text-left py-2 px-2">Algorithm</th>
                    <th className="text-right py-2 px-2">Score</th>
                    <th className="text-left py-2 px-2">Other metrics</th>
                  </tr>
                </thead>
                <tbody>
                  {models.data.map((m) => (
                    <tr key={m.id} className="border-b border-border/30">
                      <td className="py-2 px-2 font-mono">{m.algorithm}</td>
                      <td className="py-2 px-2 text-right num font-mono">
                        {formatScore(m.primary_score)}
                      </td>
                      <td className="py-2 px-2 text-xs text-muted-foreground">
                        {Object.entries(m.metrics)
                          .filter(([k]) => k !== m.primary_metric)
                          .slice(0, 3)
                          .map(([k, v]) => `${k}=${formatScore(v)}`)
                          .join(" · ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {models.data[0].feature_importance.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Feature importance — best model</CardTitle>
                <CardDescription>
                  Permutation importance against the held-out test set.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FeatureImportanceChart
                  data={models.data[0].feature_importance}
                />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
