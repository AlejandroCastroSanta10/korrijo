import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CurrentUser } from "@/lib/hooks/auth";

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.patch<CurrentUser>("/api/users/me", { name }),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    // El backend exige esta palabra exacta para confirmar el borrado.
    mutationFn: () => api.del<void>("/api/users/me", { confirm: "DELETE" }),
    onSuccess: () => {
      queryClient.clear();
    },
  });
}
