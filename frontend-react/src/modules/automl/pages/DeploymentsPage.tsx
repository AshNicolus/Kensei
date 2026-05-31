import { useQuery } from "@tanstack/react-query";
import { Globe } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { deploymentsApi } from "@/modules/automl/api/automl-api";
import { timeAgo } from "@/shared/lib/utils";

export function DeploymentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["deployments"],
    queryFn: deploymentsApi.list,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Deployments</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live prediction endpoints. Call them from anywhere with the API key
          you saved at deploy time.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : !data || data.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No deployments yet. Train a model with auto-deploy enabled.
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {data.map((d) => (
            <Card key={d.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="size-9 rounded-md bg-primary/10 grid place-items-center">
                    <Globe className="size-4 text-primary" />
                  </div>
                  <Badge variant={d.status === "active" ? "success" : "muted"}>
                    {d.status}
                  </Badge>
                </div>
                <CardTitle className="mt-3 font-mono text-sm">
                  {d.slug}
                </CardTitle>
                <CardDescription className="font-mono text-[11px] truncate">
                  {d.endpoint}
                </CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-1">
                <div>
                  Model{" "}
                  <span className="font-mono text-foreground">
                    #{d.model_id}
                  </span>{" "}
                  · key starts with{" "}
                  <span className="font-mono text-foreground">
                    {d.api_key_prefix || "—"}
                  </span>
                </div>
                <div>Deployed {timeAgo(d.created_at)}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
