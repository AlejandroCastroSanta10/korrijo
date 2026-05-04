import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useRequestMagicLink() {
  return useMutation({
    mutationFn: (email: string) =>
      api.post<void>("/auth/request-magic-link", { email }),
  });
}
