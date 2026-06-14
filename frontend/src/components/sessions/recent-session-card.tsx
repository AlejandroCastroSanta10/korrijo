"use client";

import Link from "next/link";
import { Clock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRecentSession } from "@/lib/hooks/sessions";

export default function RecentSessionCard() {
  const { data: recent } = useRecentSession();
  if (!recent) return null;

  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-primary/30 bg-primary/5 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <Clock className="size-5 shrink-0 text-primary" />
        <div className="flex min-w-0 flex-col">
          <span className="text-xs font-medium uppercase text-primary">
            Sesión más reciente
          </span>
          <span className="truncate font-medium text-foreground">
            {recent.name}
          </span>
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link href={`/app/session/${recent.id}`}>
          Acceder
          <ArrowRight className="size-4" />
        </Link>
      </Button>
    </div>
  );
}
