"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import Dropzone from "@/components/sessions/dropzone";
import { formatBytes } from "@/lib/utils";

// Coherente con el backend.
const ALLOWED_EXT = [".pdf", ".xlsx", ".txt", ".md", ".csv"];
const ACCEPT = ALLOWED_EXT.join(",");
const MAX_CONTEXT_TOTAL = 10 * 1024 * 1024; // 10 MB en total (contexto)
const MAX_DOC = 5 * 1024 * 1024; // 5 MB (examen modelo y rúbrica)

const extOk = (f: File) =>
  ALLOWED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext));
const totalSize = (fs: File[]) => fs.reduce((acc, f) => acc + f.size, 0);
const formatList = ALLOWED_EXT.join(", ");

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Ponle un nombre a la sesión.")
    .max(200, "El nombre es demasiado largo (máximo 200 caracteres)."),
  maxScore: z
    .number({ message: "Indica la puntuación máxima." })
    .min(0.1, "La puntuación máxima debe ser mayor que 0."),
  contextFiles: z
    .array(z.instanceof(File))
    .refine((fs) => fs.every(extOk), `Formatos admitidos: ${formatList}.`)
    .refine(
      (fs) => totalSize(fs) <= MAX_CONTEXT_TOTAL,
      `El contexto supera los ${formatBytes(MAX_CONTEXT_TOTAL)} en total.`,
    ),
  contextInstructions: z.string().optional(),
  modelFiles: z
    .array(z.instanceof(File))
    .min(1, "El examen modelo resuelto es obligatorio.")
    .refine((fs) => fs.every(extOk), `Formatos admitidos: ${formatList}.`)
    .refine(
      (fs) => fs.every((f) => f.size <= MAX_DOC),
      `El examen modelo supera los ${formatBytes(MAX_DOC)}.`,
    ),
  modelInstructions: z.string().optional(),
  rubricFiles: z
    .array(z.instanceof(File))
    .min(1, "La rúbrica es obligatoria.")
    .refine((fs) => fs.every(extOk), `Formatos admitidos: ${formatList}.`)
    .refine(
      (fs) => fs.every((f) => f.size <= MAX_DOC),
      `La rúbrica supera los ${formatBytes(MAX_DOC)}.`,
    ),
});

export type NewSessionValues = z.infer<typeof schema>;

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-sm text-destructive">{message}</p>;
}

function InfoHint({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label="Más información"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          <Info className="size-5" />
        </button>
      </TooltipTrigger>
      <TooltipContent>{text}</TooltipContent>
    </Tooltip>
  );
}

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "required" | "optional";
}) {
  return (
    <span
      className={
        tone === "required"
          ? "text-sm font-semibold uppercase text-destructive"
          : "text-sm font-semibold uppercase text-amber-600 dark:text-amber-500"
      }
    >
      {children}
    </span>
  );
}

interface NewSessionFormProps {
  onSubmit: (values: NewSessionValues) => void;
  disabled?: boolean;
}

export default function NewSessionForm({
  onSubmit,
  disabled = false,
}: NewSessionFormProps) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<NewSessionValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      maxScore: 10,
      contextFiles: [],
      contextInstructions: "",
      modelFiles: [],
      modelInstructions: "",
      rubricFiles: [],
    },
  });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="flex flex-col gap-8"
    >
      {/* Nombre de sesión */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="name" className="text-xl">
          Nombre de la sesión
        </Label>
        <Input
          id="name"
          className="h-12 text-lg md:text-lg"
          placeholder="Examen Historia T1 - La Prehistoria (1º BACH C)"
          aria-invalid={!!errors.name}
          disabled={disabled}
          {...register("name")}
        />
        <FieldError message={errors.name?.message} />
      </div>


      {/* Contexto */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">Contexto</h2>
          <InfoHint text="Apuntes, diapositivas o material de referencia donde estén (explícita o implícitamente) las respuestas
          a las preguntas. Límite de 10 MB entre todos los ficheros." />
          <Badge tone="optional">Opcional pero recomendable</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Controller
            control={control}
            name="contextFiles"
            render={({ field }) => (
              <Dropzone
                label="Arrastra aquí tus documentos de contexto"
                accept={ACCEPT}
                multiple
                disabled={disabled}
                invalid={!!errors.contextFiles}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <div className="flex flex-col gap-2">
            <Label htmlFor="contextInstructions" className="text-lg">
              Indicaciones adicionales{" "}
              <span className="text-sm font-normal text-muted-foreground">
                (opcional)
              </span>
            </Label>
            <Textarea
              id="contextInstructions"
              className="text-base md:text-base"
              rows={4}
              placeholder={
                'Ej.: "En el fichero de presentación no tengas en cuenta las diapositivas 25-35, están obsoletas."'
              }
              disabled={disabled}
              {...register("contextInstructions")}
            />
          </div>
        </div>
        <FieldError message={errors.contextFiles?.message} />
      </section>

      {/* Examen modelo */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">
            Examen resuelto modelo <i>(gold standard)</i>
          </h2>
          <InfoHint text="Un examen resuelto por ti. Se usará como referencia para corregir el resto. Un solo fichero (máximo 5 MB)." />
          <Badge tone="required">Obligatorio</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Controller
            control={control}
            name="modelFiles"
            render={({ field }) => (
              <Dropzone
                label="Arrastra aquí el examen modelo"
                accept={ACCEPT}
                disabled={disabled}
                invalid={!!errors.modelFiles}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <div className="flex flex-col gap-2">
            <Label htmlFor="modelInstructions" className="text-lg">
              Indicaciones adicionales{" "}
              <span className="text-sm font-normal text-muted-foreground">
                (opcional)
              </span>
            </Label>
            <Textarea
              id="modelInstructions"
              className="text-base md:text-base"
              rows={4}
              placeholder={
                'Ej.: "Si en la pregunta 2 los alumnos le dan el enfoque X también se debe dar por bueno."'
              }
              disabled={disabled}
              {...register("modelInstructions")}
            />
          </div>
        </div>
        <FieldError message={errors.modelFiles?.message} />
      </section>

      {/* Rúbrica */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">Rúbrica de corrección</h2>
          <InfoHint text="De formato libre, pero con una puntuación máxima por ítem. Se pueden incluir diferentes puntuaciones para calificar
          cada ítem (se seleccionará una en función de la correctitud de la respuesta del alumno). 
          La suma de puntos debe cuadrar con la puntuación máxima. 
          Un solo fichero (máximo 5 MB)." />
          <Badge tone="required">Obligatoria</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Controller
              control={control}
              name="rubricFiles"
              render={({ field }) => (
                <Dropzone
                  label="Arrastra aquí la rúbrica"
                  accept={ACCEPT}
                  disabled={disabled}
                  invalid={!!errors.rubricFiles}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
            <FieldError message={errors.rubricFiles?.message} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="maxScore" className="text-lg">
              Puntuación máxima
            </Label>
            <Input
              id="maxScore"
              type="number"
              min={0.1}
              step={0.1}
              className="h-12 w-32 text-lg md:text-lg"
              aria-invalid={!!errors.maxScore}
              disabled={disabled}
              {...register("maxScore", { valueAsNumber: true })}
            />
            <FieldError message={errors.maxScore?.message} />
          </div>
        </div>
      </section>

      <div className="flex items-center justify-end gap-4">
        <Button type="submit" size="lg" className="text-lg" disabled={disabled}>
          Crear sesión de corrección
        </Button>
      </div>
    </form>
  );
}
