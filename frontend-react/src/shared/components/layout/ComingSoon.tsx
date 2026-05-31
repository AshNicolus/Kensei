import { Boxes } from "lucide-react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";

interface ComingSoonProps {
  title: string;
  tagline: string;
}

export function ComingSoon({ title, tagline }: ComingSoonProps) {
  return (
    <div className="grid place-items-center min-h-[60vh]">
      <Card className="max-w-lg w-full text-center border-dashed">
        <CardContent className="py-12 px-8 flex flex-col items-center gap-4">
          <div className="size-14 rounded-xl bg-primary/10 grid place-items-center">
            <Boxes className="size-6 text-primary" />
          </div>
          <Badge variant="outline" className="text-[10px] uppercase tracking-widest">
            On the roadmap
          </Badge>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
            {tagline}
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            This module is part of the Kensei platform vision —
            <br /> currently in design.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
