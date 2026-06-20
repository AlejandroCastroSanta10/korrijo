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
  // Vacío está permitido: equivale a quitar el nombre.
  name: z
    .string()
    .trim()
    .max(75, "El nombre es demasiado largo (máximo 75 caracteres)."),
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
        Modificar tu información personal
      </h2>
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="flex max-w-2xl flex-col gap-5"
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="name" className="text-lg">
            Nombre
          </Label>
          <Input
            id="name"
            className="h-12 text-xl md:text-lg"
            aria-invalid={!!errors.name}
            disabled={updateProfile.isPending}
            {...register("name")}
          />
          {errors.name && (
            <p className="text-sm text-destructive">{errors.name.message}</p>
          )}
        </div>

        <div>
          <Button
            type="submit"
            size="lg"
            className="text-base"
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
          <span className="text-lg font-semibold">Eliminar tu cuenta <i>Korrijo</i></span>
          <span className="text-base">
            Se borrarán para siempre todos tus datos y sesiones. Esta acción no
            se puede deshacer.
          </span>
        </div>
        <Button
          variant="destructive"
          size="lg"
          className="shrink-0 text-base"
          onClick={() => setOpen(true)}
        >
          Quiero borrar mi cuenta
        </Button>
      </div>

      <Dialog open={open} onOpenChange={(o) => !o && closeDialog()}>
        <DialogContent className="gap-0 p-10 sm:max-w-3xl">
          <DialogHeader className="items-center gap-4 pr-0 text-center">
            <div className="flex size-16 items-center justify-center rounded-full bg-destructive/10 ring-8 ring-destructive/5">
              <TriangleAlert className="size-8 text-destructive" />
            </div>
            <DialogTitle className="text-3xl text-foreground">
              Eliminar tu cuenta <i>Korrijo</i>
            </DialogTitle>
            <DialogDescription className="max-w-xl text-lg leading-relaxed text-muted-foreground">
              Esta acción es <b className="text-foreground">irreversible</b>: se
              eliminarán tu cuenta y todas tus sesiones de corrección.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-8 flex flex-col gap-3 rounded-2xl border border-input bg-muted/50 p-5">
            <p className="text-base">
              Si estás segur@, escribe{" "}
              <code className="rounded  px-1.5 py-0.5 font-mono text-sm font-semibold text-foreground">
                {expected}
              </code>{" "}
              en este campo:
            </p>
            <Input
              autoFocus
              className="h-12 bg-background text-lg"
              value={confirmation}
              disabled={deleteAccount.isPending}
              onChange={(e) => setConfirmation(e.target.value)}
            />
          </div>

          <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-center">
            <Button
              variant="outline"
              size="lg"
              className="text-base sm:min-w-40"
              onClick={closeDialog}
              disabled={deleteAccount.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              size="lg"
              className="text-base sm:min-w-40"
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
      <h1 className="text-4xl font-bold text-foreground sm:text-4xl">
        Configuración
      </h1>

      <ProfileSection defaultName={user.name ?? ""} email={user.email} />
      <Separator />
      <DangerZone email={user.email} />
    </section>
  );
}
