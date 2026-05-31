import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Database } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { datasetsApi } from "@/modules/automl/api/automl-api";
import { formatBytes, formatNumber, timeAgo } from "@/shared/lib/utils";

export function DatasetsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: datasetsApi.list,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Datasets</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Every CSV you've uploaded. Drop new ones from the{" "}
          <Link to="/automl/autopilot" className="text-primary hover:underline">
            Autopilot page
          </Link>
          .
        </p>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No datasets yet.
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((d) => (
            <Card key={d.id} className="hover:border-primary/40 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="size-9 rounded-md bg-primary/10 grid place-items-center">
                    <Database className="size-4 text-primary" />
                  </div>
                  <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
                    #{d.id}
                  </span>
                </div>
                <CardTitle className="mt-3 truncate">{d.name}</CardTitle>
                <CardDescription className="font-mono text-[11px] truncate">
                  {d.filename}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-2 text-xs">
                <Field label="Rows" value={formatNumber(d.rows)} />
                <Field label="Cols" value={d.columns.toString()} />
                <Field label="Size" value={formatBytes(d.size_bytes)} />
                <div className="col-span-3 text-muted-foreground text-[11px] mt-1">
                  Uploaded {timeAgo(d.created_at)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="num font-mono">{value}</div>
    </div>
  );
}
