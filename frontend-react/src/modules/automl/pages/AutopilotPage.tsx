import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  Copy,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import { Separator } from "@/shared/components/ui/separator";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { apiError } from "@/shared/lib/api";
import {
  autopilotApi,
  datasetsApi,
} from "@/modules/automl/api/automl-api";
import type {
  AutopilotResponse,
  Dataset,
  Preset,
} from "@/modules/automl/api/types";
import { formatNumber, formatPct, formatScore } from "@/shared/lib/utils";
import { Dropzone } from "@/modules/automl/components/Dropzone";
import { FeatureImportanceChart } from "@/modules/automl/components/FeatureImportanceChart";

const PRESETS: { value: Preset; label: string; eta: string; blurb: string }[] = [
  { value: "quick", label: "Quick", eta: "~30s", blurb: "Two algos, a few trials" },
  { value: "balanced", label: "Balanced", eta: "~2m", blurb: "Full sweep, tuned" },
  { value: "thorough", label: "Thorough", eta: "~10m", blurb: "Deep search, best score" },
];

export function AutopilotPage() {
  const queryClient = useQueryClient();
  const [activeDataset, setActiveDataset] = useState<Dataset | null>(null);
  const [target, setTarget] = useState<string>("");
  const [preset, setPreset] = useState<Preset>("balanced");
  const [autoDeploy, setAutoDeploy] = useState<boolean>(true);
  const [deploySlug, setDeploySlug] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number | undefined>();
  const [result, setResult] = useState<AutopilotResponse | null>(null);

  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: datasetsApi.list,
  });

  // Auto-select the most recent dataset if none selected yet
  useEffect(() => {
    if (!activeDataset && datasetsQuery.data && datasetsQuery.data.length) {
      setActiveDataset(datasetsQuery.data[0]);
    }
  }, [datasetsQuery.data, activeDataset]);

  const analysisQuery = useQuery({
    queryKey: ["analyze", activeDataset?.id],
    queryFn: () => autopilotApi.analyze(activeDataset!.id),
    enabled: !!activeDataset,
  });

  // Apply the suggested target whenever a new analysis arrives
  useEffect(() => {
    if (analysisQuery.data?.suggested_target) {
      setTarget(analysisQuery.data.suggested_target);
    }
  }, [analysisQuery.data]);

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      datasetsApi.upload(file, (p) => setUploadProgress(p)),
    onSuccess: (ds) => {
      setUploadProgress(undefined);
      setActiveDataset(ds);
      setResult(null);
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      toast.success(`Uploaded ${ds.name} (${formatNumber(ds.rows)} rows)`);
    },
    onError: (e) => {
      setUploadProgress(undefined);
      toast.error(apiError(e));
    },
  });

  const trainMutation = useMutation({
    mutationFn: () =>
      autopilotApi.train({
        dataset_id: activeDataset!.id,
        target,
        preset,
        auto_deploy: autoDeploy,
        deploy_slug: deploySlug.trim() || null,
      }),
    onSuccess: (r) => {
      setResult(r);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["deployments"] });
      if (r.job.status === "succeeded") {
        toast.success(`Best model: ${r.best_model?.algorithm}`);
      } else if (r.job.status === "failed") {
        toast.error(r.job.message || "Training failed");
      }
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const analysis = analysisQuery.data;
  const columns = analysis?.columns ?? [];
  const targetColumns = useMemo(() => columns.map((c) => c.name), [columns]);

  return (
    <div className="space-y-8">
      {/* Headline */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground uppercase tracking-widest mb-2">
            <Sparkles className="size-3 text-primary" /> Autopilot
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            From CSV to deployed API in one click
          </h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
            Drop a dataset. We analyze it, pick a target, run multiple algorithms
            with hyperparameter search, evaluate them, and serve the best one as
            an authenticated prediction endpoint.
          </p>
        </div>
      </div>

      {/* Step 1 — pick a dataset (upload or reuse) */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <span className="text-muted-foreground font-mono text-xs">01</span>
                Dataset
              </CardTitle>
              <CardDescription>
                Drop a CSV here or pick one of your previous uploads.
              </CardDescription>
            </div>
            {datasetsQuery.data && datasetsQuery.data.length > 0 && (
              <div className="min-w-[14rem]">
                <Select
                  value={activeDataset?.id?.toString() ?? ""}
                  onValueChange={(v) => {
                    const ds = datasetsQuery.data!.find(
                      (d) => d.id.toString() === v
                    );
                    if (ds) {
                      setActiveDataset(ds);
                      setResult(null);
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Pick a dataset" />
                  </SelectTrigger>
                  <SelectContent>
                    {datasetsQuery.data!.map((d) => (
                      <SelectItem key={d.id} value={d.id.toString()}>
                        {d.name} · {formatNumber(d.rows)} rows
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <Dropzone
            onFile={(f) => uploadMutation.mutate(f)}
            uploading={uploadMutation.isPending}
            uploadProgress={uploadProgress}
          />
        </CardContent>
      </Card>

      {/* Step 2 — analysis */}
      {activeDataset && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-muted-foreground font-mono text-xs">02</span>
              At a glance
            </CardTitle>
            <CardDescription>
              {activeDataset.name} ·{" "}
              <span className="num">{formatNumber(activeDataset.rows)}</span>{" "}
              rows × {activeDataset.columns} columns
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {analysisQuery.isLoading ? (
              <div className="grid grid-cols-3 gap-3">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-20" />
                ))}
              </div>
            ) : analysis ? (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <Metric label="Rows" value={formatNumber(analysis.rows)} />
                  <Metric label="Columns" value={analysis.columns_count.toString()} />
                  <Metric
                    label="Suggested target"
                    value={analysis.suggested_target ?? "—"}
                    mono
                  />
                  <Metric
                    label="Task"
                    value={analysis.suggested_task_type ?? "—"}
                  />
                </div>
                {analysis.warnings.length > 0 && (
                  <div className="space-y-1.5">
                    {analysis.warnings.map((w) => (
                      <div
                        key={w}
                        className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2 flex items-start gap-2"
                      >
                        <TriangleAlert className="size-3.5 mt-0.5 shrink-0" />
                        {w}
                      </div>
                    ))}
                  </div>
                )}
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    Show column-by-column breakdown
                  </summary>
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="text-muted-foreground">
                        <tr className="border-b border-border/60">
                          <th className="text-left py-2 px-2 font-medium">Name</th>
                          <th className="text-left py-2 px-2 font-medium">Type</th>
                          <th className="text-right py-2 px-2 font-medium">Unique</th>
                          <th className="text-right py-2 px-2 font-medium">Missing</th>
                          <th className="text-left py-2 px-2 font-medium">Sample</th>
                        </tr>
                      </thead>
                      <tbody className="font-mono">
                        {columns.map((c) => (
                          <tr key={c.name} className="border-b border-border/30">
                            <td className="py-1.5 px-2">
                              {c.name}
                              {c.id_like && (
                                <span className="ml-1 text-[10px] text-muted-foreground">
                                  (id)
                                </span>
                              )}
                              {c.constant && (
                                <span className="ml-1 text-[10px] text-muted-foreground">
                                  (constant)
                                </span>
                              )}
                            </td>
                            <td className="py-1.5 px-2 text-muted-foreground">
                              {c.dtype}
                            </td>
                            <td className="py-1.5 px-2 text-right num">
                              {c.unique}
                            </td>
                            <td className="py-1.5 px-2 text-right text-muted-foreground num">
                              {c.missing > 0 ? formatPct(c.missing_pct) : "—"}
                            </td>
                            <td className="py-1.5 px-2 text-muted-foreground truncate max-w-[16rem]">
                              {c.sample_values.slice(0, 3).map(String).join(", ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Step 3 — train */}
      {activeDataset && analysis && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-muted-foreground font-mono text-xs">03</span>
              Train
            </CardTitle>
            <CardDescription>
              We'll pick algorithms and trials for you. You can override below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>What do you want to predict?</Label>
                <Select value={target} onValueChange={setTarget}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose target column" />
                  </SelectTrigger>
                  <SelectContent>
                    {targetColumns.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Speed</Label>
                <div className="grid grid-cols-3 gap-2">
                  {PRESETS.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setPreset(p.value)}
                      className={`text-left rounded-md border px-3 py-2 transition-colors ${
                        preset === p.value
                          ? "border-primary bg-primary/10"
                          : "border-border hover:bg-accent/60"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{p.label}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {p.eta}
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        {p.blurb}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <Separator />

            <div className="flex items-start justify-between gap-4">
              <div className="space-y-0.5">
                <Label htmlFor="auto-deploy" className="cursor-pointer">
                  Auto-deploy the best model
                </Label>
                <p className="text-xs text-muted-foreground">
                  Generates an authenticated API endpoint as soon as training
                  finishes.
                </p>
              </div>
              <Switch
                id="auto-deploy"
                checked={autoDeploy}
                onCheckedChange={setAutoDeploy}
              />
            </div>
            {autoDeploy && (
              <div className="space-y-1.5">
                <Label htmlFor="slug">
                  Endpoint name{" "}
                  <span className="text-muted-foreground text-xs">
                    (optional, auto-generated if empty)
                  </span>
                </Label>
                <Input
                  id="slug"
                  value={deploySlug}
                  onChange={(e) => setDeploySlug(e.target.value)}
                  placeholder={`${activeDataset.name.toLowerCase().replace(/\s+/g, "-")}-v1`}
                  className="font-mono"
                />
              </div>
            )}

            <Button
              size="lg"
              className="w-full"
              disabled={!target || trainMutation.isPending}
              onClick={() => trainMutation.mutate()}
            >
              {trainMutation.isPending ? (
                <>
                  <svg
                    className="size-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeOpacity="0.25"
                    />
                    <path
                      d="M22 12a10 10 0 0 1-10 10"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                  </svg>
                  Training…
                </>
              ) : (
                <>
                  Start training
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 4 — result */}
      {result && (
        <ResultBlock result={result} />
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-card/60 px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div
        className={`mt-1 text-base num ${mono ? "font-mono" : "font-medium"}`}
      >
        {value}
      </div>
    </div>
  );
}

function ResultBlock({ result }: { result: AutopilotResponse }) {
  const job = result.job;
  const best = result.best_model;

  if (job.status !== "succeeded" || !best) {
    return (
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">
            Training {job.status}
          </CardTitle>
          <CardDescription>{job.message ?? "—"}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <Card className="border-primary/40 bg-primary/[0.03]">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Check className="size-4 text-primary" />
                Best model: <span className="font-mono">{best.algorithm}</span>
              </CardTitle>
              <CardDescription>
                Trained on {result.chose_target} ·{" "}
                {result.chose_task_type} · {result.chose_trials} trials
              </CardDescription>
            </div>
            <Badge variant="success">
              {best.primary_metric}={formatScore(best.primary_score)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(best.metrics)
              .slice(0, 4)
              .map(([k, v]) => (
                <Metric key={k} label={k} value={formatScore(v)} mono />
              ))}
          </div>

          {best.feature_importance.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-widest text-muted-foreground mb-3">
                Why the model predicts this — top features
              </div>
              <FeatureImportanceChart data={best.feature_importance} />
            </div>
          )}
        </CardContent>
      </Card>

      {result.deployment_slug && result.deployment_api_key && (
        <DeploymentBanner
          slug={result.deployment_slug}
          endpoint={result.deployment_endpoint!}
          apiKey={result.deployment_api_key}
        />
      )}
    </div>
  );
}

function DeploymentBanner({
  slug,
  endpoint,
  apiKey,
}: {
  slug: string;
  endpoint: string;
  apiKey: string;
}) {
  const curl = `curl -X POST ${window.location.origin}${endpoint} \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"rows":[{...}]}'`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your live endpoint</CardTitle>
        <CardDescription>
          API key is shown once. Save it now.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <CopyRow label="Endpoint" value={endpoint} />
        <CopyRow label="API key" value={apiKey} secret />
        <div>
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
            Call it
          </div>
          <pre className="text-xs font-mono bg-secondary/40 border border-border/60 rounded-md p-3 overflow-x-auto leading-relaxed">
            {curl}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}

function CopyRow({
  label,
  value,
  secret,
}: {
  label: string;
  value: string;
  secret?: boolean;
}) {
  const [revealed, setRevealed] = useState(!secret);
  const display = revealed ? value : "•".repeat(Math.min(value.length, 24));
  return (
    <div className="rounded-md border border-border/60 bg-card/40 flex items-center gap-2 px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground w-20 shrink-0">
        {label}
      </div>
      <code className="text-xs flex-1 truncate font-mono">{display}</code>
      {secret && (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setRevealed((v) => !v)}
        >
          {revealed ? "Hide" : "Show"}
        </Button>
      )}
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          navigator.clipboard.writeText(value);
          toast.success(`${label} copied`);
        }}
      >
        <Copy className="size-3.5" />
      </Button>
    </div>
  );
}
