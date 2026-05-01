import ContactForm from "@/components/contact/contact-form";

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 flex flex-col gap-10">
      <div className="flex flex-col gap-3">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          Contacto
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
          Si tienes alguna duda, házmela saber a través del siguiente formulario.
          Te responderé lo antes posible.
        </p>
      </div>

      <ContactForm />
    </div>
  );
}
