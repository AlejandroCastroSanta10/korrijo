"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
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

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-sm text-destructive">{message}</p>;
}

export default function ContactForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
  });

  function onSubmit(_data: ContactFormValues) {
    toast.info("Funcionalidad pendiente. El envío real estará disponible próximamente.");
    reset();
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {/* Nombre */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="nombre">
            Nombre <span className="text-destructive">*</span>
          </Label>
          <Input
            id="nombre"
            type="text"
            placeholder="Tu nombre"
            {...register("nombre")}
          />
          <FieldError message={errors.nombre?.message} />
        </div>

        {/* Apellidos */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="apellidos">
            Apellidos{" "}
            <span className="text-zinc-400 text-xs font-normal">(opcional)</span>
          </Label>
          <Input
            id="apellidos"
            type="text"
            placeholder="Tus apellidos"
            {...register("apellidos")}
          />
        </div>
      </div>

      {/* Email */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">
          Email <span className="text-destructive">*</span>
        </Label>
        <Input
          id="email"
          type="email"
          placeholder="tu@email.com"
          {...register("email")}
        />
        <FieldError message={errors.email?.message} />
      </div>

      {/* Asunto */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="asunto">
          Asunto <span className="text-destructive">*</span>
        </Label>
        <Input
          id="asunto"
          type="text"
          placeholder="¿Sobre qué tienes dudas o quieres escribirme?"
          {...register("asunto")}
        />
        <FieldError message={errors.asunto?.message} />
      </div>

      {/* Mensaje */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="mensaje">
          Mensaje <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="mensaje"
          placeholder="Escribe tu mensaje aquí..."
          rows={6}
          {...register("mensaje")}
        />
        <FieldError message={errors.mensaje?.message} />
      </div>

      <Button type="submit" className="w-full sm:w-fit" disabled={!isValid}>
        Enviar
      </Button>
    </form>
  );
}
