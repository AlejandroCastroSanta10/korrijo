import { Play, ClipboardList, Upload, Check } from "lucide-react";
import AuthForm from "@/components/auth/auth-form";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";

const steps = [
  {
    icon: ClipboardList,
    number: 1,
    description: (
      <>
        Al crear una <b>sesión de corrección</b> debes subir:
        <ul className="mx-auto mt-3 w-fit list-disc space-y-1 pl-5 text-left">
          <li>Documentos con <b>contexto</b>, por ejemplo apuntes o diapositivas (opcionales)</li>
          <li><b>Examen resuelto</b> a modo de modelo (obligatorio)</li>
          <li><b>Rúbrica</b> de corrección (obligatoria)</li>
        </ul>
      </>
    ),
  },
  {
    icon: Upload,
    number: 2,
    description: (
      <p>Posteriormente ya podrás adjuntar los <b>exámenes</b> que quieras que se corrijan automáticamente</p>
    )
  },
  {
    icon: Check,
    number: 3,
    description: (
      <p>Para cada examen <i>Korrijo</i> proporciona un informe con feedback sobre la corrección y la rúbrica rellenada con una calificación propuesta</p>
    )
  },
];

const faqs = [
  {
    id: "tipos-examen",
    question: "¿Qué tipos de examen puedo corregir?",
    answer:
      "De momento solo sirve para exámenes de preguntas de desarrollo o cortas, es decir, aquellas en las que el alumno tiene que escribir un texto con uno o varios párrafos como respuesta.",
  },
  {
    id: "nota-definitiva",
    question: "¿La nota que da Korrijo es definitiva?",
    answer:
      "No. Korrijo propone una calificación basada en la rúbrica, pero la decisión final siempre es del profesor. Las correcciones pueden contener errores al estar generadas por IA.",
  },
  {
    id: "formato-examenes",
    question: "¿En qué formato debo subir los exámenes?",
    answer:
      "Los exámenes deben subirse en formato PDF o imagen. Cada archivo debe contener un único examen manuscrito escaneado o fotografiado con buena resolución.",
  },
];

export default function LandingPage() {
  return (
    <>
      {/* Sección 1: auth */}
      <section
        id="auth"
        className="flex flex-1 flex-col gap-12 px-6 py-16 max-w-7xl mx-auto w-full scroll-mt-20"
      >
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          <span className="block">Céntrate en enseñar.</span>
          <span className="block text-primary">
            <i>Korrijo</i> se encarga del resto.
          </span>
        </h1>

        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[4fr_5fr]">
          <div className="flex flex-col justify-center items-center">
            <AuthForm />
          </div>

          {/* TODO: sustituir por vídeo demo en v0.2.0 */}
          <div className="flex items-center justify-center rounded-2xl border border-zinc-200 bg-zinc-100 min-h-[500px] dark:border-zinc-700 dark:bg-zinc-800">
            <Play className="size-16 text-zinc-400" />
          </div>
        </div>
      </section>

      {/* Sección 2: about (Sobre la herramienta) */}
      <section
        id="about"
        className="bg-zinc-50 dark:bg-zinc-900 px-6 py-20 scroll-mt-20"
      >
        <div className="mx-auto max-w-5xl flex flex-col gap-12">
          <div className="flex flex-col items-center gap-4 text-center">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl">
              Conoce a <i>Korrijo</i>
            </h2>
            <p className="max-w-2xl text-lg text-zinc-700 dark:text-zinc-300">
              <i>Korrijo</i> es un sistema para <b>profesores</b> que facilita la corrección
              de <b>pruebas evaluativas manuscritas</b> gracias a herramientas de IA.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            {steps.map(({ icon: Icon, number, description }) => (
              <div key={number} className="flex flex-col items-center gap-4 text-center h-full">
                <Icon className="size-12 text-zinc-900 dark:text-zinc-100" strokeWidth={1.75} />
                <div className="flex-1 text-base text-zinc-700 dark:text-zinc-300">{description}</div>
                <span className="text-4xl font-bold text-zinc-600 dark:text-zinc-300">
                  {number}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sección 3: FAQs */}
      <section id="faqs" className="px-6 py-20 scroll-mt-20">
        <div className="mx-auto max-w-3xl flex flex-col gap-12">
          <h2 className="text-3xl font-bold tracking-tight text-center text-zinc-900 dark:text-zinc-50 sm:text-4xl">
            Preguntas frecuentes (FAQs)
          </h2>

          <Accordion type="single" collapsible>
            {faqs.map(({ id, question, answer }) => (
              <AccordionItem key={id} value={id}>
                <AccordionTrigger className="text-lg font-medium">
                  {question}
                </AccordionTrigger>
                <AccordionContent className="text-base">{answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>
    </>
  );
}
