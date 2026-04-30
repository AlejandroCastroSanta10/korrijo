"use client";

import { toast } from "sonner";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "success"; data: HealthResponse }
  | { kind: "error"; message: string };

export default function DesignCheckPage() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    fetchHealth()
      .then((data) => setStatus({ kind: "success", data }))
      .catch((err: unknown) =>
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "Error desconocido",
        }),
      );
  }, []);

  return (
    <main className="container mx-auto max-w-3xl space-y-10 p-8">
      <header>
        <h1 className="text-3xl font-bold">Design check</h1>
        <p className="text-muted-foreground">
          Página interna para verificar que los componentes y el tema se ven coherentes.
          Se eliminará al cerrar la milestone v0.1.0.
        </p>
      </header>

      <Separator />

      {/* Botones */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Buttons</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link</Button>
        </div>
      </section>

      <Separator />

      {/* Inputs */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Form fields</h2>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="ejemplo@correo.com" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="message">Mensaje</Label>
          <Textarea id="message" placeholder="Escribe aquí..." />
        </div>
      </section>

      <Separator />

      {/* Card */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Card</h2>
        <Card>
          <CardHeader>
            <CardTitle>Título de la card</CardTitle>
            <CardDescription>Descripción breve de la card.</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Contenido principal de la card.</p>
          </CardContent>
        </Card>
      </section>

      <Separator />

      {/* Accordion */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Accordion</h2>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger>¿Qué es Korrijo?</AccordionTrigger>
            <AccordionContent>
              Un sistema para corregir exámenes manuscritos con ayuda de IA.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-2">
            <AccordionTrigger>¿Quién puede usarlo?</AccordionTrigger>
            <AccordionContent>
              Profesores que quieran agilizar la corrección de pruebas evaluativas.
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      <Separator />

      {/* Toast */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Toast (Sonner)</h2>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => toast("Mensaje de prueba")}>Toast simple</Button>
          <Button variant="outline" onClick={() => toast.success("¡Funcionó!")}>
            Toast success
          </Button>
          <Button variant="destructive" onClick={() => toast.error("Algo falló")}>
            Toast error
          </Button>
        </div>
      </section>

      {/* Conectividad con el backend */}
      <section className="space-y-3">
        <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
          <main className="flex flex-col items-center gap-4 rounded-2xl border border-zinc-200 bg-white p-10 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Estado del backend
            </h1>

            {status.kind === "loading" && (
              <p className="text-zinc-500">Comprobando conexión…</p>
            )}

            {status.kind === "success" && (
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <span className="text-lg">✓</span>
                <span className="font-mono text-sm">
                  {JSON.stringify(status.data)}
                </span>
              </div>
            )}

            {status.kind === "error" && (
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                <span className="text-lg">✗</span>
                <span className="text-sm">{status.message}</span>
              </div>
            )}
          </main>
        </div>
      </section>
    </main>
  );
}