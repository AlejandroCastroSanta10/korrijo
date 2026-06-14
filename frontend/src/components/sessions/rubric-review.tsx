"use client";

import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import type { RubricItem } from "@/lib/hooks/sessions";

const SUM_TOLERANCE = 0.01; // misma tolerancia que el backend

const itemSchema = z.object({
  name: z.string().trim().min(1, "Indica un nombre para el ítem."),
  max_score: z
    .number({ message: "Puntos" })
    .min(0, "Los puntos no pueden ser negativos."),
  description: z.string(),
});

const schema = z.object({
  items: z.array(itemSchema).min(1, "La rúbrica debe tener al menos un ítem."),
});

type RubricFormValues = z.infer<typeof schema>;

interface RubricReviewProps {
  maxScore: number;
  initialItems: RubricItem[];
  initialWarning: string | null;
  onConfirm: (items: RubricItem[]) => void;
  confirming?: boolean;
  error?: string | null;
}

export default function RubricReview({
  maxScore,
  initialItems,
  initialWarning,
  onConfirm,
  confirming = false,
  error,
}: RubricReviewProps) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<RubricFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      items:
        initialItems.length > 0
          ? initialItems
          : [{ name: "", max_score: 0, description: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  // Total en vivo para avisar si no cuadra con la puntuación máxima.
  const items = useWatch({ control, name: "items" }) ?? [];
  const total = items.reduce((acc, it) => acc + (Number(it.max_score) || 0), 0);
  const mismatch = Math.abs(total - maxScore) > SUM_TOLERANCE;

  return (
    <form
      onSubmit={handleSubmit((data) => onConfirm(data.items))}
      noValidate
      className="flex flex-col gap-6"
    >
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
          Revisión de la rúbrica
        </h2>
        <p className="text-base text-muted-foreground">
          Esto es lo que la IA ha extraído de tu rúbrica. Corrige lo que necesites
          antes de continuar. Estos ítems se usarán para corregir los exámenes.
        </p>
      </div>

      {initialWarning && (
        <p className="flex items-start gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>{initialWarning}</span>
        </p>
      )}

      <ul className="flex flex-col gap-4">
        {fields.map((field, index) => (
          <li
            key={field.id}
            className="flex flex-col gap-4 rounded-2xl border border-input bg-input/20 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Ítem {index + 1}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Quitar ítem ${index + 1}`}
                disabled={confirming}
                onClick={() => remove(index)}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_8rem]">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor={`item-${index}-name`} className="text-base">
                  Criterio
                </Label>
                <Input
                  id={`item-${index}-name`}
                  className="h-11 text-base"
                  placeholder="P. ej. Definición de prehistoria"
                  aria-invalid={!!errors.items?.[index]?.name}
                  {...register(`items.${index}.name`)}
                />
                {errors.items?.[index]?.name && (
                  <p className="text-xs text-destructive">
                    {errors.items[index]?.name?.message}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor={`item-${index}-score`} className="text-base">
                  Puntuación máxima
                </Label>
                <Input
                  id={`item-${index}-score`}
                  type="number"
                  min={0}
                  step={0.1}
                  className="h-11 text-base"
                  aria-invalid={!!errors.items?.[index]?.max_score}
                  {...register(`items.${index}.max_score`, {
                    valueAsNumber: true,
                  })}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor={`item-${index}-desc`} className="text-base">
                Descripción{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  (opcional)
                </span>
              </Label>
              <Textarea
                id={`item-${index}-desc`}
                rows={2}
                placeholder="Qué se valora en este criterio y cómo se reparten los puntos."
                {...register(`items.${index}.description`)}
              />
            </div>
          </li>
        ))}
      </ul>

      {errors.items?.root && (
        <p className="text-xs text-destructive">{errors.items.root.message}</p>
      )}

      <Button
        type="button"
        variant="outline"
        className="self-start"
        disabled={confirming}
        onClick={() => append({ name: "", max_score: 0, description: "" })}
      >
        <Plus className="size-4" />
        Añadir ítem
      </Button>

      <div
        className={
          mismatch
            ? "flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-amber-500/10 px-5 py-4 text-amber-700 dark:text-amber-400"
            : "flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-muted px-5 py-4 text-foreground"
        }
      >
        <span className="text-lg font-semibold">
          Total: {total.toLocaleString("es")} / {maxScore.toLocaleString("es")}{" "}
          puntos
        </span>
        {mismatch && (
          <span className="flex items-center gap-1.5 text-sm font-medium">
            <TriangleAlert className="size-4" />
            La suma debe cuadrar con la puntuación máxima que has indicado
          </span>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end">
        <Button
          type="submit"
          size="lg"
          className="text-base"
          disabled={confirming || mismatch}
        >
          {confirming ? "Validando..." : "Confirmar rúbrica y continuar"}
        </Button>
      </div>
    </form>
  );
}
