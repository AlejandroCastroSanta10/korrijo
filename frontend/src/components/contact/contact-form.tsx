"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

const schema = z.object({
  nombre: z
    .string()
    .min(1, "El nombre es obligatorio")
    .max(80, "El nombre no puede superar los 80 caracteres"),
  apellidos: z
    .string()
    .max(120, "Los apellidos no pueden superar los 120 caracteres")
    .optional(),
  email: z
    .string()
    .min(1, "El email es obligatorio")
    .email("Introduce un email válido")
    .max(254, "El email no puede superar los 254 caracteres"),
  asunto: z
    .string()
    .min(1, "El asunto es obligatorio")
    .max(150, "El asunto no puede superar los 150 caracteres"),
  mensaje: z
    .string()
    .min(1, "El mensaje es obligatorio")
    .max(2000, "El mensaje no puede superar los 2000 caracteres"),
});

type ContactFormValues = z.infer<typeof schema>;

const labelClass = "text-base text-zinc-900 dark:text-zinc-50";
const fieldClass = "h-11 text-base md:text-base";

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-sm text-destructive">{message}</p>;
}

export default function ContactForm() {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isValid, isSubmitting },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
  });

  const mensajeLength = watch("mensaje")?.length ?? 0;

  async function onSubmit(data: ContactFormValues) {
    try {
      await api.post("/contact", {
        name: data.nombre,
        last_name: data.apellidos || null,
        email: data.email,
        subject: data.asunto,
        message: data.mensaje,
      });
      toast.success("Mensaje enviado correctamente.");
      reset();
    } catch (error) {
      let message = "No se pudo conectar con el servidor. Inténtalo más tarde.";
      if (error instanceof ApiError) {
        message =
          error.status === 429
            ? "Has enviado demasiados mensajes. Espera un poco si quieres enviar más."
            : "No se pudo enviar el mensaje. Inténtalo de nuevo.";
      }
      toast.error(message);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-8 sm:grid-cols-2">
        {/* Nombre */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="nombre" className={labelClass}>
            Nombre <span className="text-destructive">*</span>
          </Label>
          <Input
            id="nombre"
            type="text"
            placeholder="Juan"
            maxLength={80}
            className={fieldClass}
            {...register("nombre")}
          />
          <FieldError message={errors.nombre?.message} />
        </div>

        {/* Apellidos */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="apellidos" className={labelClass}>
            Apellidos{" "}
            <span className="text-muted-foreground text-sm font-normal">(opcional)</span>
          </Label>
          <Input
            id="apellidos"
            type="text"
            placeholder="Pérez Castillo"
            maxLength={120}
            className={fieldClass}
            {...register("apellidos")}
          />
        </div>
      </div>

      {/* Email */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="email" className={labelClass}>
          Email <span className="text-destructive">*</span>
        </Label>
        <Input
          id="email"
          type="email"
          placeholder="jpc1980@gmail.com"
          maxLength={254}
          className={fieldClass}
          {...register("email")}
        />
        <FieldError message={errors.email?.message} />
      </div>

      {/* Asunto */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="asunto" className={labelClass}>
          Asunto <span className="text-destructive">*</span>
        </Label>
        <Input
          id="asunto"
          type="text"
          placeholder="¿Sobre qué tienes dudas o quieres escribirme?"
          maxLength={150}
          className={fieldClass}
          {...register("asunto")}
        />
        <FieldError message={errors.asunto?.message} />
      </div>

      {/* Mensaje */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="mensaje" className={labelClass}>
          Mensaje <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="mensaje"
          placeholder="Escribe tu mensaje aquí..."
          rows={7}
          maxLength={2000}
          className="text-base md:text-base"
          {...register("mensaje")}
        />
        <div className="flex items-center justify-between gap-2">
          <FieldError message={errors.mensaje?.message} />
          <span className="ml-auto text-sm text-muted-foreground tabular-nums">
            {mensajeLength}/2000
          </span>
        </div>
      </div>

      <Button
        type="submit"
        size="lg"
        className="w-full sm:w-fit"
        disabled={!isValid || isSubmitting}
      >
        {isSubmitting ? "Enviando..." : "Enviar"}
      </Button>
    </form>
  );
}
