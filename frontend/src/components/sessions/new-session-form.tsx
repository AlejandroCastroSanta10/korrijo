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

// Formatos admitidos por campo (coherente con el backend).
const TEXT_EXT = [".pdf", ".md", ".txt"]; // contexto y examen modelo
const RUBRIC_EXT = [".pdf", ".xlsx", ".csv", ".md"]; // rúbrica
const MAX_CONTEXT_TOTAL = 7 * 1024 * 1024; // 7 MB en total (contexto)
const MAX_DOC = 3 * 1024 * 1024; // 3 MB (examen modelo y rúbrica)
const MAX_INSTRUCTIONS = 250; // caracteres por campo de indicaciones

const extOk = (f: File, exts: string[]) =>
  exts.some((ext) => f.name.toLowerCase().endsWith(ext));
const acceptOf = (exts: string[]) => exts.join(",");
const listOf = (exts: string[]) => exts.join(", ");
const totalSize = (fs: File[]) => fs.reduce((acc, f) => acc + f.size, 0);

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Ponle un nombre a la sesión.")
    .max(200, "El nombre es demasiado largo (máximo 200 caracteres)."),
  maxScore: z
    .number({ message: "Indica la puntuación máxima para este examen." })
    .min(0.1, "La puntuación máxima debe ser mayor que 0."),
  contextFiles: z
    .array(z.instanceof(File))
    .refine(
      (fs) => fs.every((f) => extOk(f, TEXT_EXT)),
      `Formatos admitidos: ${listOf(TEXT_EXT)}.`,
    )
    .refine(
      (fs) => totalSize(fs) <= MAX_CONTEXT_TOTAL,
      `Los ficheros de contexto superan los ${formatBytes(MAX_CONTEXT_TOTAL)} en total.`,
    ),
  contextInstructions: z
    .string()
    .max(
      MAX_INSTRUCTIONS,
      `Las indicaciones no pueden superar los ${MAX_INSTRUCTIONS} caracteres.`,
    )
    .optional(),
  modelFiles: z
    .array(z.instanceof(File))
    .min(1, "El examen modelo resuelto es obligatorio.")
    .refine(
      (fs) => fs.every((f) => extOk(f, TEXT_EXT)),
      `Formatos admitidos: ${listOf(TEXT_EXT)}.`,
    )
    .refine(
      (fs) => fs.every((f) => f.size <= MAX_DOC),
      `El examen modelo resuelto supera los ${formatBytes(MAX_DOC)}.`,
    ),
  modelInstructions: z
    .string()
    .max(
      MAX_INSTRUCTIONS,
      `Las indicaciones no pueden superar los ${MAX_INSTRUCTIONS} caracteres.`,
    )
    .optional(),
  rubricFiles: z
    .array(z.instanceof(File))
    .min(1, "La rúbrica es obligatoria.")
    .refine(
      (fs) => fs.every((f) => extOk(f, RUBRIC_EXT)),
      `Formatos admitidos: ${listOf(RUBRIC_EXT)}.`,
    )
    .refine(
      (fs) => fs.every((f) => f.size <= MAX_DOC),
      `La rúbrica supera los ${formatBytes(MAX_DOC)}.`,
    ),
});

export type NewSessionValues = z.infer<typeof schema>;

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-medium text-destructive">{message}</p>;
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
        "ml-2 inline-flex items-center rounded-full px-3 py-0.5 text-xs font-semibold uppercase tracking-wide " +
        (tone === "required"
          ? "bg-primary text-primary-foreground"
          : "border border-border bg-muted text-muted-foreground")
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
    watch,
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

  const contextLen = (watch("contextInstructions") ?? "").length;
  const modelLen = (watch("modelInstructions") ?? "").length;

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
      <section className="flex flex-col gap-3 mt-6">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">CONTEXTO</h2>
          <InfoHint text="Apuntes, diapositivas o material de referencia donde estén (explícita o implícitamente) las respuestas
          a las preguntas del examen. Límite de 7 MB entre todos los ficheros." />
          <Badge tone="optional">Opcional pero recomendable</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Controller
            control={control}
            name="contextFiles"
            render={({ field }) => (
              <Dropzone
                label="Arrastra aquí tus documentos de contexto (ficheros .pdf, .md o .txt)"
                accept={acceptOf(TEXT_EXT)}
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
              maxLength={MAX_INSTRUCTIONS}
              placeholder={
                'Ej: "El documento de apuntes que te he proporcionado cubre todo el temario del examen, no exijas más nivel. Cualquier respuesta que use terminología equivalente a la aquí empleada debe aceptarse como válida."'
              }
              disabled={disabled}
              {...register("contextInstructions")}
            />
            <div className="flex items-center justify-between">
              <FieldError message={errors.contextInstructions?.message} />
              <span className="ml-auto text-sm text-muted-foreground">
                {contextLen}/{MAX_INSTRUCTIONS}
              </span>
            </div>
          </div>
        </div>
        <FieldError message={errors.contextFiles?.message} />
      </section>

      {/* Examen modelo */}
      <section className="flex flex-col gap-3 mt-6">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">
            EXAMEN RESUELTO MODELO <i>(gold standard)</i>
          </h2>
          <InfoHint text="Un examen resuelto por ti a ordenador. Se usará como referencia para corregir el resto. Un solo fichero (máximo 3 MB)." />
          <Badge tone="required">Obligatorio</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Controller
            control={control}
            name="modelFiles"
            render={({ field }) => (
              <Dropzone
                label="Arrastra aquí el examen modelo (fichero .pdf, .md o .txt)"
                accept={acceptOf(TEXT_EXT)}
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
              maxLength={MAX_INSTRUCTIONS}
              placeholder={
                'Ej: "Quizá algunas de las respuestas que se proporcionan en este modelo resuelto que te he proporcionado son un poco largas, no exijas esa rigurosidad al alumno."'
              }
              disabled={disabled}
              {...register("modelInstructions")}
            />
            <div className="flex items-center justify-between">
              <FieldError message={errors.modelInstructions?.message} />
              <span className="ml-auto text-sm text-muted-foreground">
                {modelLen}/{MAX_INSTRUCTIONS}
              </span>
            </div>
          </div>
        </div>
        <FieldError message={errors.modelFiles?.message} />
      </section>

      {/* Rúbrica */}
      <section className="flex flex-col gap-3 mt-6">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">RÚBRICA DE CORRECCIÓN</h2>
          <InfoHint text="De formato libre, pero con un listado de ítems, cada uno con su puntuación máxima. 
          Se pueden incluir diferentes categorías para calificar
          cada ítem (en este caso para puntuarlo se seleccionará la que el sistema crea adecuada). 
          La suma de las puntuaciones máximas de los ítems debe cuadrar con la puntuación máxima de examen que introduzcas. 
          Un solo fichero (máximo 3 MB)." />
          <Badge tone="required">Obligatoria</Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Controller
              control={control}
              name="rubricFiles"
              render={({ field }) => (
                <Dropzone
                  label="Arrastra aquí la rúbrica (fichero .pdf, .xlsx, .csv o .md)"
                  accept={acceptOf(RUBRIC_EXT)}
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
              Puntuación máxima del examen
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

      <div className="flex items-center justify-end gap-4 mt-4">
        <Button
          type="submit"
          size="lg"
          className="h-11 px-12 text-xl"
          disabled={disabled}
        >
          Crear sesión de corrección
        </Button>
      </div>
    </form>
  );
}
