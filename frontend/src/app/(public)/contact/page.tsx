import ContactForm from "@/components/contact/contact-form";

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 flex flex-col gap-10">
      <div className="flex flex-col gap-3">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          Formulario de contacto
        </h1>
        <p className="text-lg text-zinc-900 dark:text-zinc-50 leading-relaxed mt-4">
          Si tienes alguna duda, házmela saber a través del este formulario.
          Te responderé al email que proporciones lo antes posible.
        </p>
      </div>

      <ContactForm />
    </div>
  );
}
