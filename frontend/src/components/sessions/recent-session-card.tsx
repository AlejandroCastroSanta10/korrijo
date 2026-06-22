"use client";

import Link from "next/link";
import { Clock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRecentSession } from "@/lib/hooks/sessions";

export default function RecentSessionCard() {
  const { data: recent } = useRecentSession();
  if (!recent) return null;

  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border-2 border-primary/50 bg-primary/10 px-6 py-3 shadow-sm ring-1 ring-primary/10">
      <div className="flex min-w-0 items-center gap-4">
        <Clock className="size-6 shrink-0 text-primary" />
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-sm font-semibold uppercase tracking-wide text-primary">
            Sesión en la que has trabajado más recientemente:
          </span>
          <span className="truncate text-lg font-semibold text-foreground">
            {recent.name}
          </span>
        </div>
      </div>
      <Button asChild size="lg" className="shrink-0 text-base">
        <Link href={`/app/session/${recent.id}`}>
          Acceder
          <ArrowRight className="size-5" />
        </Link>
      </Button>
    </div>
  );
}
