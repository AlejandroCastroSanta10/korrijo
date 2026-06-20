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
  nombre: z.string().min(1, "El nombre es obligatorio"),
  apellidos: z.string().optional(),
  email: z
    .string()
    .min(1, "El email es obligatorio")
    .email("Introduce un email válido"),
  asunto: z.string().min(1, "El asunto es obligatorio"),
  mensaje: z.string().min(1, "El mensaje es obligatorio"),
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
    formState: { errors, isValid, isSubmitting },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
  });

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
          className="text-base md:text-base"
          {...register("mensaje")}
        />
        <FieldError message={errors.mensaje?.message} />
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
