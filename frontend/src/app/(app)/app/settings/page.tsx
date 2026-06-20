"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useCurrentUser } from "@/lib/hooks/auth";
import { useDeleteAccount, useUpdateProfile } from "@/lib/hooks/user";

const profileSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "El nombre no puede estar vacío.")
    .max(200, "El nombre es demasiado largo (máximo 200 caracteres)."),
});

type ProfileValues = z.infer<typeof profileSchema>;

function ProfileSection({
  defaultName,
  email,
}: {
  defaultName: string;
  email: string;
}) {
  const updateProfile = useUpdateProfile();
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: defaultName },
  });

  const onSubmit = (values: ProfileValues) => {
    updateProfile.mutate(values.name, {
      onSuccess: () => toast.success("Información personal actualizada."),
      onError: () =>
        toast.error("No se pudieron guardar los cambios. Inténtalo de nuevo."),
    });
  };

  return (
    <section className="flex flex-col gap-5 mt-4">
      <h2 className="text-2xl font-semibold text-foreground">
        Tu información personal
      </h2>
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="flex max-w-md flex-col gap-5"
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="name" className="text-base">
            Nombre
          </Label>
          <Input
            id="name"
            className="h-11 text-base"
            aria-invalid={!!errors.name}
            disabled={updateProfile.isPending}
            {...register("name")}
          />
          {errors.name && (
            <p className="text-xs text-destructive">{errors.name.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="email" className="text-base">
            Email{" "}
            <span className="text-xs font-normal text-muted-foreground">
              (no editable)
            </span>
          </Label>
          <Input
            id="email"
            className="h-11 text-base"
            value={email}
            readOnly
            disabled
          />
        </div>

        <div>
          <Button
            type="submit"
            disabled={!isDirty || updateProfile.isPending}
          >
            {updateProfile.isPending && (
              <Loader2 className="size-4 animate-spin" />
            )}
            Guardar cambios
          </Button>
        </div>
      </form>
    </section>
  );
}

function DangerZone({ email }: { email: string }) {
  const router = useRouter();
  const deleteAccount = useDeleteAccount();
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");

  const expected = `ELIMINAR/${email}`;
  const canDelete = confirmation === expected && !deleteAccount.isPending;

  const closeDialog = () => {
    if (deleteAccount.isPending) return;
    setOpen(false);
    setConfirmation("");
  };

  const handleDelete = () => {
    if (!canDelete) return;
    deleteAccount.mutate(undefined, {
      onSuccess: () => {
        toast.success("Tu cuenta se ha eliminado correctamente.");
        router.replace("/login");
      },
      onError: () =>
        toast.error("No se pudo eliminar la cuenta. Inténtalo de nuevo."),
    });
  };

  return (
    <section className="flex flex-col gap-5">
      <h2 className="text-2xl font-semibold text-foreground"><i>Danger zone</i></h2>
      <div className="flex flex-col gap-4 rounded-2xl border border-destructive/40 bg-destructive/5 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <span className="font-semibold">Eliminar cuenta</span>
          <span className="text-sm">
            Se borrarán para siempre todos tus datos y sesiones. Esta acción no
            se puede deshacer.
          </span>
        </div>
        <Button
          variant="destructive"
          className="shrink-0"
          onClick={() => setOpen(true)}
        >
          Quiero borrar mi cuenta
        </Button>
      </div>

      <Dialog open={open} onOpenChange={(o) => !o && closeDialog()}>
        <DialogContent className="gap-6 p-8 sm:max-w-2xl">
          <DialogHeader className="gap-3">
            <DialogTitle className="flex items-center gap-2 text-2xl text-destructive">
              <TriangleAlert className="size-6" />
              ¿Seguro/a que quieres eliminar tu cuenta <i>Korrijo</i>? 
            </DialogTitle>
            <DialogDescription className="text-base leading-relaxed">
              Esta acción es <b>irreversible</b>: se eliminarán tu cuenta y todas
              tus sesiones de corrección. Para continuar, escribe{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm text-foreground">
                {expected}
              </code>{" "}
              en el campo de abajo.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Input
              autoFocus
              className="h-11 text-base"
              placeholder={expected}
              value={confirmation}
              disabled={deleteAccount.isPending}
              onChange={(e) => setConfirmation(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={closeDialog}
              disabled={deleteAccount.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={!canDelete}
            >
              {deleteAccount.isPending && (
                <Loader2 className="size-4 animate-spin" />
              )}
              Eliminar cuenta definitivamente
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}

export default function SettingsPage() {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading || !user) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <Loader2 className="size-10 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-12">
      <h1 className="text-3xl font-bold text-foreground sm:text-4xl">
        Configuración
      </h1>

      <ProfileSection defaultName={user.name ?? ""} email={user.email} />
      <Separator />
      <DangerZone email={user.email} />
    </section>
  );
}
