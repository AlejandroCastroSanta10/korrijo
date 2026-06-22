"use client";

import { useState } from "react";
import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import type { RubricItem } from "@/lib/hooks/sessions";

const SUM_TOLERANCE = 0.01; // misma tolerancia que el backend
const MAX_NAME = 100; // caracteres máximos para el criterio de ítem
const MAX_DESC = 800; // caracteres máximos para descripción de ítem

const itemSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Indica un nombre para el ítem.")
    .max(MAX_NAME, `El criterio no puede superar los ${MAX_NAME} caracteres.`),
  max_score: z
    .number({ message: "Puntos" })
    .min(0, "Los puntos no pueden ser negativos."),
  description: z
    .string()
    .trim()
    .min(1, "La descripción es obligatoria.")
    .max(MAX_DESC, `La descripción no puede superar los ${MAX_DESC} caracteres.`),
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

  const [toRemove, setToRemove] = useState<number | null>(null);

  // Total en vivo para avisar si no cuadra con la puntuación máxima.
  const items = useWatch({ control, name: "items" }) ?? [];
  const total = items.reduce((acc, it) => acc + (Number(it.max_score) || 0), 0);
  const mismatch = Math.abs(total - maxScore) > SUM_TOLERANCE;
  // No se puede continuar si algún ítem no tiene criterio o descripción.
  const incomplete = items.some(
    (it) => !it.name?.trim() || !it.description?.trim(),
  );
  // Ni si algún ítem tiene una puntuación de 0 (o no válida).
  const zeroScore = items.some((it) => !(Number(it.max_score) > 0));

  // Etiqueta del ítem que se va a quitar.
  const removingLabel =
    toRemove !== null
      ? items[toRemove]?.name?.trim() || `el ítem ${toRemove + 1}`
      : "";

  const confirmRemove = () => {
    if (toRemove !== null) remove(toRemove);
    setToRemove(null);
  };

  return (
    <>
    <form
      onSubmit={handleSubmit((data) => onConfirm(data.items))}
      noValidate
      className="flex flex-col gap-6"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-bold text-foreground sm:text-4xl">
          Revisión de la rúbrica
        </h2>
        <p className="text-lg mt-6">
          Esto es lo que el sistema ha extraído de tu rúbrica. Revísalo y corrige lo que necesites
          antes de continuar. <i>Korrijo</i> usará estos <i>ítems</i> para puntuar los exámenes de
          esta sesión de corrección. La descripción de <i>ítem</i> indica aspectos que tiene que tener el
          sistema en cuenta a la hora de puntuar ese <i>ítem</i>. 
        </p>
      </div>

      <ul className="flex flex-col gap-4 mt-6">
        {fields.map((field, index) => (
          <li
            key={field.id}
            className="flex flex-col gap-5 rounded-2xl border border-input bg-input/20 p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-base font-semibold uppercase tracking-wide text-muted-foreground">
                Ítem {index + 1}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Quitar ítem ${index + 1}`}
                disabled={confirming}
                onClick={() => setToRemove(index)}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="size-5" />
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-[1fr_9rem]">
              <div className="flex flex-col gap-2">
                <Label htmlFor={`item-${index}-name`} className="text-lg">
                  Criterio
                </Label>
                <Input
                  id={`item-${index}-name`}
                  className="h-12 text-lg md:text-lg"
                  maxLength={MAX_NAME}
                  placeholder="P. ej. Definición de prehistoria"
                  aria-invalid={!!errors.items?.[index]?.name}
                  {...register(`items.${index}.name`)}
                />
                {errors.items?.[index]?.name && (
                  <p className="text-sm text-destructive">
                    {errors.items[index]?.name?.message}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor={`item-${index}-score`} className="text-lg">
                  Puntuación máxima
                </Label>
                <Input
                  id={`item-${index}-score`}
                  type="number"
                  min={0}
                  step={0.1}
                  className="h-12 text-lg md:text-lg"
                  aria-invalid={!!errors.items?.[index]?.max_score}
                  {...register(`items.${index}.max_score`, {
                    valueAsNumber: true,
                  })}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor={`item-${index}-desc`} className="text-lg">
                Descripción
              </Label>
              <Textarea
                id={`item-${index}-desc`}
                rows={3}
                maxLength={MAX_DESC}
                className="text-base md:text-base"
                placeholder="Describe brevemente qué evalúa este ítem. Si la rúbrica plantea categorías (p. ej. Bien 1 p, Regular 0,5 p, Mal 0 p; o con porcentajes con respecto a la puntuación máxima del ítem), inclúyelas aquí para que se tengan en cuenta al corregir."
                aria-invalid={!!errors.items?.[index]?.description}
                {...register(`items.${index}.description`)}
              />
              <div className="flex items-center justify-between gap-2">
                {errors.items?.[index]?.description ? (
                  <p className="text-sm text-destructive">
                    {errors.items[index]?.description?.message}
                  </p>
                ) : (
                  <span />
                )}
                <span className="ml-auto text-sm text-muted-foreground">
                  {(items[index]?.description ?? "").length}/{MAX_DESC}
                </span>
              </div>
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
        size="lg"
        className="self-start border-2 text-lg mt-4 mb-4"
        disabled={confirming}
        onClick={() => append({ name: "", max_score: 0, description: "" })}
      >
        <Plus className="size-5" />
        Añadir ítem
      </Button>

      <div
        className={
          mismatch || incomplete || zeroScore
            ? "flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-amber-500/50 bg-amber-500/10 px-6 py-5 text-amber-700 shadow-sm dark:text-amber-400"
            : "flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-emerald-500/50 bg-emerald-500/10 px-6 py-5 text-emerald-700 shadow-sm dark:text-emerald-400"
        }
      >
        <span className="text-2xl">
          Suma de los ítems: <b>{total.toLocaleString("es")}</b> / Puntuación máxima del examen: <b>{maxScore.toLocaleString("es")}</b>
        </span>
        {(mismatch || incomplete || zeroScore) && (
          <span className="flex items-center gap-1.5 text-base font-medium">
            <TriangleAlert className="size-5" />
            {mismatch
              ? "La suma debe cuadrar con la puntuación máxima que has indicado"
              : incomplete
                ? "Cada ítem debe tener un criterio y una descripción"
                : "Cada ítem debe tener una puntuación mayor que 0"}
          </span>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end">
        <Button
          type="submit"
          size="lg"
          className="text-lg mt-4"
          disabled={confirming || mismatch || incomplete || zeroScore}
        >
          {confirming ? "Cargando..." : "Confirmar y crear sesión de corrección"}
        </Button>
      </div>
    </form>

      <Dialog
        open={toRemove !== null}
        onOpenChange={(open) => !open && setToRemove(null)}
      >
        <DialogContent className="gap-7 p-10 sm:max-w-2xl">
          <DialogHeader className="gap-3">
            <DialogTitle className="text-3xl">¿Quitar este ítem?</DialogTitle>
            <DialogDescription className="text-lg leading-relaxed mt-2">
              Vas a quitar <b>{removingLabel}</b> de la rúbrica de corrección. Se perderá lo que
              hayas escrito en él, aunque podrás volver a añadirlo manualmente.
            </DialogDescription>
          </DialogHeader>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              size="lg"
              variant="outline"
              className="text-base sm:min-w-40"
              onClick={() => setToRemove(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              size="lg"
              variant="destructive"
              className="text-base sm:min-w-40"
              onClick={confirmRemove}
            >
              <Trash2 className="size-4" />
              Quitar ítem
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
