import { NavLink, useLocation } from "react-router-dom";
import {
  Boxes,
  Database,
  Globe,
  GraduationCap,
  LayoutGrid,
  Play,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AUTOML_NAV: NavItem[] = [
  { to: "/automl/autopilot", label: "Autopilot", icon: Sparkles },
  { to: "/automl/datasets", label: "Datasets", icon: Database },
  { to: "/automl/jobs", label: "Jobs", icon: Workflow },
  { to: "/automl/deployments", label: "Deployments", icon: Globe },
  { to: "/automl/predict", label: "Predict", icon: Play },
];

const MODULES = [
  {
    key: "automl",
    label: "AutoML",
    description: "CSV → API",
    icon: Zap,
    available: true,
    path: "/automl/autopilot",
  },
  {
    key: "pretraining",
    label: "Pretraining",
    description: "Foundation models",
    icon: Boxes,
    available: false,
    path: "/pretraining",
  },
  {
    key: "finetuning",
    label: "Fine-tuning",
    description: "Adapt LLMs",
    icon: GraduationCap,
    available: false,
    path: "/finetuning",
  },
];

export function Sidebar() {
  const location = useLocation();
  const activeModule = MODULES.find((m) =>
    location.pathname.startsWith(`/${m.key}`)
  )?.key ?? "automl";

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border/60 bg-background/40 backdrop-blur">
      <div className="px-5 h-14 flex items-center gap-2 border-b border-border/60">
        <div className="size-7 rounded-md bg-primary/15 grid place-items-center">
          <LayoutGrid className="size-4 text-primary" />
        </div>
        <div className="leading-tight">
          <div className="font-semibold tracking-tight">Kensei</div>
          <div className="text-[10px] uppercase text-muted-foreground tracking-widest">
            ML Platform
          </div>
        </div>
      </div>

      <div className="px-3 py-4">
        <div className="px-2 mb-2 text-[10px] uppercase tracking-widest text-muted-foreground">
          Modules
        </div>
        <div className="space-y-1">
          {MODULES.map((m) => {
            const Icon = m.icon;
            const isActive = activeModule === m.key;
            const inner = (
              <div
                className={cn(
                  "group flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                )}
              >
                <Icon className="size-4 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="leading-tight truncate">{m.label}</div>
                  <div className="text-[10px] text-muted-foreground/80 truncate">
                    {m.description}
                  </div>
                </div>
                {!m.available && (
                  <span className="text-[9px] uppercase tracking-wider rounded-sm border border-border px-1 py-0.5 text-muted-foreground">
                    Soon
                  </span>
                )}
              </div>
            );
            return m.available ? (
              <NavLink key={m.key} to={m.path}>
                {inner}
              </NavLink>
            ) : (
              <NavLink key={m.key} to={m.path}>
                {inner}
              </NavLink>
            );
          })}
        </div>
      </div>

      {activeModule === "automl" && (
        <div className="px-3 pb-4 flex-1 overflow-auto scrollbar-hide">
          <div className="px-2 mb-2 text-[10px] uppercase tracking-widest text-muted-foreground">
            AutoML
          </div>
          <nav className="space-y-0.5">
            {AUTOML_NAV.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                      isActive
                        ? "bg-primary/15 text-primary"
                        : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                    )
                  }
                >
                  <Icon className="size-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </div>
      )}

      <div className="mt-auto p-3 border-t border-border/60">
        <div className="rounded-md border border-border/60 bg-secondary/40 p-3">
          <div className="text-xs font-medium">Free tier</div>
          <div className="text-[11px] text-muted-foreground leading-relaxed mt-1">
            Unlimited training on datasets up to 1M rows during private beta.
          </div>
        </div>
      </div>
    </aside>
  );
}
