import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Play } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { apiError } from "@/shared/lib/api";
import { deploymentsApi } from "@/modules/automl/api/automl-api";
import { toast } from "sonner";

export function PredictPage() {
  const { data: deployments, isLoading } = useQuery({
    queryKey: ["deployments"],
    queryFn: deploymentsApi.list,
  });

  const [slug, setSlug] = useState<string>("");
  const [apiKey, setApiKey] = useState("");
  const [text, setText] = useState<string>(
    JSON.stringify([{ feature_1: 0, feature_2: 0 }], null, 2)
  );

  const rows = useMemo(() => {
    try {
      const parsed = JSON.parse(text);
      return Array.isArray(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }, [text]);

  const predictMutation = useMutation({
    mutationFn: () => deploymentsApi.predict(slug, rows ?? [], apiKey || undefined),
    onError: (e) => toast.error(apiError(e)),
  });

  if (isLoading) return <Skeleton className="h-40" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Predict</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Test a deployed model with sample rows.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Make a prediction</CardTitle>
          <CardDescription>
            Pick a deployment, paste the API key, send JSON rows.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!deployments || deployments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No deployments yet.
            </p>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label>Deployment</Label>
                <Select value={slug} onValueChange={setSlug}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a deployment" />
                  </SelectTrigger>
                  <SelectContent>
                    {deployments.map((d) => (
                      <SelectItem key={d.slug} value={d.slug}>
                        {d.slug} · model #{d.model_id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>API key</Label>
                <Input
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  type="password"
                  placeholder="ks_…"
                  className="font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Rows (JSON array)</Label>
                <textarea
                  className="font-mono text-xs w-full rounded-md border border-input bg-background px-3 py-2 min-h-[160px] focus:outline-none focus:ring-1 focus:ring-ring"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
                {rows === null && (
                  <p className="text-xs text-destructive">Invalid JSON.</p>
                )}
              </div>
              <Button
                onClick={() => predictMutation.mutate()}
                disabled={!slug || rows === null || predictMutation.isPending}
              >
                {predictMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Play className="size-4" />
                )}
                Send
              </Button>

              {predictMutation.data && (
                <pre className="text-xs font-mono bg-secondary/40 border border-border/60 rounded-md p-3 overflow-x-auto">
                  {JSON.stringify(predictMutation.data, null, 2)}
                </pre>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
