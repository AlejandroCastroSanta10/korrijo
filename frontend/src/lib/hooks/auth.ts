import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface CurrentUser {
  id: string;
  email: string;
  name: string | null;
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<CurrentUser>("/auth/me"),
    retry: false,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout", {}),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["auth"] });
    },
  });
}

export function useRequestMagicLink() {
  return useMutation({
    mutationFn: (email: string) =>
      api.post<void>("/auth/request-magic-link", { email }),
  });
}

export function useVerifyMagicLink() {
  return useMutation({
    mutationFn: (token: string) =>
      api.post<{ id: string; email: string; name: string }>("/auth/verify", {
        token,
      }),
  });
}
