import { LayoutGrid } from "lucide-react";
import type { ReactNode } from "react";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  footer: ReactNode;
  children: ReactNode;
}

export function AuthLayout({ title, subtitle, footer, children }: AuthLayoutProps) {
  return (
    <div className="surface-gradient min-h-screen grid lg:grid-cols-2">
      {/* Left — brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 border-r border-border/60">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-md bg-primary/15 grid place-items-center">
            <LayoutGrid className="size-4 text-primary" />
          </div>
          <span className="font-semibold tracking-tight text-lg">Kensei</span>
        </div>
        <div className="space-y-6 max-w-md">
          <h1 className="text-4xl font-semibold tracking-tight leading-tight">
            Train and deploy ML models
            <br />
            <span className="text-primary">in one click.</span>
          </h1>
          <p className="text-muted-foreground leading-relaxed">
            Drop a CSV. Kensei picks the target, runs Optuna across the best
            algorithms, evaluates them with cross-validation, and gives you a
            live prediction API — under a minute, no code.
          </p>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {[
              "Auto target detection + task inference",
              "5+ algorithms, hyperparameter-tuned",
              "Per-feature explanations included",
              "Deployed as an authenticated API",
            ].map((line) => (
              <li key={line} className="flex items-center gap-2">
                <span className="size-1 rounded-full bg-primary inline-block" />
                {line}
              </li>
            ))}
          </ul>
        </div>
        <div className="text-xs text-muted-foreground font-mono">
          v0.1.0 · private beta
        </div>
      </div>

      {/* Right — form */}
      <div className="flex flex-col justify-center px-6 sm:px-12 py-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-10">
            <div className="size-8 rounded-md bg-primary/15 grid place-items-center">
              <LayoutGrid className="size-4 text-primary" />
            </div>
            <span className="font-semibold tracking-tight text-lg">Kensei</span>
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground mt-1.5">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-8 text-sm text-muted-foreground text-center">
            {footer}
          </div>
        </div>
      </div>
    </div>
  );
}
