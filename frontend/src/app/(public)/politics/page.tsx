const sections = [
  { id: "terms", label: "Términos de uso" },
  { id: "privacy", label: "Política de privacidad" },
  { id: "cookies", label: "Política de cookies" },
  { id: "ai", label: "Uso de IA" },
];

export default function PoliticsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 flex flex-col gap-16">
      <div className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          Términos y políticas
        </h1>

        {/* Índice */}
        <nav className="flex flex-col gap-1 mt-10">
          {sections.map(({ id, label }) => (
            <a
              key={id}
              href={`#${id}`}
              className="text-sm text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50 transition-colors w-fit"
            >
              {label}
            </a>
          ))}
        </nav>
      </div>

      {/* Términos de uso */}
      <section id="terms" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Términos de uso
        </h2>
        <div className="flex flex-col gap-4 text-zinc-900 dark:text-zinc-50 leading-relaxed">
          <p>
            <i>Korrijo</i> es una herramienta de apoyo a la corrección de
            exámenes manuscritos destinada principalmente a docentes y centros
            educativos. El acceso y uso del servicio implica la aceptación de
            los presentes términos.
          </p>
          <p>
            El usuario se compromete a utilizar la plataforma únicamente con
            fines educativos y de evaluación académica. Queda prohibido subir
            contenido que no corresponda a exámenes o documentos de carácter
            educativo, así como cualquier uso que vulnere la privacidad de
            terceros o la normativa vigente. <i>Korrijo</i> no garantiza la
            exactitud de las correcciones generadas y no se hace responsable de
            las decisiones de calificación adoptadas por el docente basándose en
            los resultados de la herramienta.
          </p>
        </div>
      </section>

      {/* Política de privacidad */}
      <section id="privacy" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Política de privacidad
        </h2>
        <div className="flex flex-col gap-4 text-zinc-900 dark:text-zinc-50 leading-relaxed">
          <p>
            Para el funcionamiento del servicio se recogen únicamente los datos
            estrictamente necesarios: dirección de correo electrónico para la
            autentificación, los archivos subidos por el usuario (exámenes,
            rúbricas y documentos de contexto) y otros datos que se piden al crear una sesión de corrección. 
            Estos datos se utilizan
            exclusivamente para prestar el servicio solicitado y no se ceden ni
            venden a terceros.
          </p>
          <p>
            Los archivos subidos se almacenan hasta que se borre la sesión de corrección correspondiente. 
            Los datos de cuenta se conservan mientras el usuario no la elimine.
          </p>
        </div>
      </section>

      {/* Política de cookies */}
      <section id="cookies" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Política de cookies
        </h2>
        <div className="flex flex-col gap-4 text-zinc-900 dark:text-zinc-50 leading-relaxed">
          <p>
            <i>Korrijo</i> utiliza únicamente cookies técnicas de sesión,
            imprescindibles para el correcto funcionamiento de la plataforma.
            Estas cookies permiten mantener la sesión iniciada del usuario
            durante su visita y no recogen información personal más allá de la
            necesaria para este fin.
          </p>
          <p>
            No se emplean cookies de seguimiento, publicidad ni análisis de
            comportamiento de ningún tipo. Al utilizar la plataforma, el usuario
            acepta el uso de estas cookies técnicas.
          </p>
        </div>
      </section>

      {/* Uso de IA */}
      <section id="ai" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Uso de IA
        </h2>
        <div className="flex flex-col gap-4 text-zinc-900 dark:text-zinc-50 leading-relaxed">
          <p>
            Las calificaciones propuestas y los informes
            generados por <i>Korrijo</i> son producidos gracias a modelos de
            inteligencia artificial. Como cualquier sistema que use IA, los
            resultados pueden contener errores, imprecisiones o interpretaciones
            incorrectas de las respuestas del alumno.
          </p>
          <p>
            La calificación final es siempre responsabilidad exclusiva del
            docente. <i>Korrijo</i> actúa como herramienta que permite agilizar
            estas correcciones, pero no como criterio definitivo de evaluación. 
            Se recomienda enormemente contrastar de manera manual todo el <i>feedback</i> generado con
            los exámenes antes de comunicar cualquier nota al alumnado.
          </p>
        </div>
      </section>
    </div>
  );
}
