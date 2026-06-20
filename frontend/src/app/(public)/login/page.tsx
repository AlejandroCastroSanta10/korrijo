import { ClipboardList, Upload, Check } from "lucide-react";
import Image from "next/image";
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
        Para crear una <b>sesión de corrección</b> debes subir:
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
      <p>En una segunda fase ya podrás adjuntar los <b>exámenes</b> que quieras que se corrijan automáticamente</p>
    )
  },
  {
    icon: Check,
    number: 3,
    description: (
      <p>Para cada examen corregido exitosamente <i>Korrijo</i> proporciona un informe con <i>feedback</i> para el profesor y 
      la rúbrica rellenada con una calificación orientativa propuesta</p>
    )
  },
];

const faqs = [
  {
    id: "tipos-examen",
    question: "¿Qué tipos de examen puedo corregir?",
    answer:
      "De momento la herramienta solo sirve para exámenes con respuestas manuscritas que estén formados íntegramente por preguntas de desarrollo y/o cortas, es decir, aquellas en las que el alumno tiene que escribir un texto con uno o varios párrafos como respuesta.",
  },
  {
    id: "nota-definitiva",
    question: "¿La calificaciones que proporciona la aplicación son de fiar?",
    answer:
      "Las nota nota que se propone para un examen es orientativa y calculada con herramientas de IA a partir de la documentación inicial (rúbrica, examen modelo, etc.). La evaluación final siempre corresponde al profesor. La idea es que la retroalimentación que se le proporciona al docente le permita agilizar las correcciones, pero en ningún caso sustituir su criterio.",
  },
  {
    id: "formato-examenes",
    question: "¿Qué formato deben tener los exámenes que puede procesar la herramienta?",
    answer:
      "Las pruebas evaluativas deben subirse escaneadas en formato PDF o imagen (.png, .jpg, .jpeg). Cada archivo debe contener un único examen. En cada examen debe aparecer en la parte de arriba un título de examen y, opcionalmente, nombre y apellidos, grupo, fecha y DNI. Abajo, cada pregunta junto al espacio para que el alumno responda.",
  },
];

export default function LandingPage() {
  return (
    <>
      {/* Sección 1: auth */}
      <section
        id="auth"
        className="flex flex-col gap-12 px-6 py-16 max-w-7xl mx-auto w-full scroll-mt-20"
      >
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          <span className="block">Céntrate en enseñar.</span>
          <span className="block text-primary">
            Agiliza las correcciones de exámenes.
          </span>
        </h1>

        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[2fr_5fr]">
          <div className="flex flex-col justify-center items-center">
            <AuthForm />
          </div>

          <div className="flex flex-col gap-4">
            <div className="relative min-h-[460px] overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 lg:min-h-[560px]">
              <Image
                src="/images/korrijo-landing-image.png"
                alt="Imagen de una sesión de corrección de Korrijo"
                fill
                priority
                sizes="(min-width: 1024px) 71vw, 100vw"
                className="object-cover"
              />
            </div>
            <p className="text-center text-lg italic text-zinc-600 dark:text-zinc-400">
              Sube tus exámenes. Obtén calificaciones orientativas y feedback tras las correcciones.
            </p>
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
              de <b>pruebas evaluativas manuscritas</b> gracias al uso de herramientas de IA.
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
