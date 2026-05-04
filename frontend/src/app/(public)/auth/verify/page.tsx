import { Suspense } from "react";
import { VerifyContent } from "./verify-content"

export default function VerifyPage() {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <Suspense fallback={<VerifyingState />}>
        <VerifyContent />
      </Suspense>
    </div>
  );
}

function VerifyingState() {
  return (
    <p className="text-sm text-zinc-500 dark:text-zinc-400">Verificando...</p>
  );
}
