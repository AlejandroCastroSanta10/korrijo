import { Play } from "lucide-react";
import AuthForm from "@/components/auth/auth-form";

export default function LandingPage() {
  return (
    <section
      id="auth"
      className="flex flex-1 flex-col gap-12 px-6 py-16 max-w-7xl mx-auto w-full"
    >
      <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
        <span className="block">Céntrate en enseñar.</span>
        <span className="block text-primary">
          <i>Korrijo</i> se encarga del resto.
        </span>
      </h1>

      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[1fr_2fr]">
        <div className="flex flex-col justify-center items-center">
          <AuthForm />
        </div>

        {/* TODO: sustituir por vídeo demo en v0.2.0 */}
        <div className="flex items-center justify-center rounded-2xl border border-zinc-200 bg-zinc-100 min-h-[500px] dark:border-zinc-700 dark:bg-zinc-800">
          <Play className="size-16 text-zinc-400" />
        </div>
      </div>
    </section>
  );
}
