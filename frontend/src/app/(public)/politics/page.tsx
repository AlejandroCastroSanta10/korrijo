const sections = [
  { id: "terminos", label: "Términos de uso" },
  { id: "privacidad", label: "Política de privacidad" },
  { id: "cookies", label: "Política de cookies" },
  { id: "ia", label: "Uso de IA" },
];

export default function PoliticsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 flex flex-col gap-16">
      <div className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          Términos y políticas
        </h1>

        <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
          <strong>MVP académico (TFG).</strong> Los textos que figuran en
          esta página son un borrador orientativo. Los documentos legales
          definitivos se redactarán por un profesional antes de cualquier
          despliegue en producción.
        </div>

        {/* Índice */}
        <nav className="flex flex-col gap-1">
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
      <section id="terminos" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Términos de uso
        </h2>
        <div className="flex flex-col gap-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
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
      <section id="privacidad" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Política de privacidad
        </h2>
        <div className="flex flex-col gap-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
          <p>
            Para el funcionamiento del servicio se recogen únicamente los datos
            estrictamente necesarios: dirección de correo electrónico para la
            autenticación y los archivos subidos por el usuario (exámenes,
            rúbricas y documentos de contexto). Estos datos se utilizan
            exclusivamente para prestar el servicio solicitado y no se ceden ni
            venden a terceros.
          </p>
          <p>
            Los archivos subidos se almacenan de forma temporal durante el
            tiempo necesario para procesar las correcciones. Los datos de
            cuenta se conservan mientras el usuario mantenga una sesión activa.
            El usuario puede solicitar la eliminación de su cuenta y de todos
            sus datos en cualquier momento contactando a través del formulario
            de contacto.
          </p>
        </div>
      </section>

      {/* Política de cookies */}
      <section id="cookies" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Política de cookies
        </h2>
        <div className="flex flex-col gap-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
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
      <section id="ia" className="flex flex-col gap-4 scroll-mt-20">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Uso de IA
        </h2>
        <div className="flex flex-col gap-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
          <p>
            Las correcciones, calificaciones propuestas e informes de feedback
            generados por <i>Korrijo</i> son producidos por un modelo de
            inteligencia artificial. Como cualquier sistema de IA, los
            resultados pueden contener errores, imprecisiones o interpretaciones
            incorrectas de las respuestas del alumno.
          </p>
          <p>
            La calificación final es siempre responsabilidad exclusiva del
            docente. <i>Korrijo</i> actúa como herramienta de apoyo, no como
            árbitro definitivo de la evaluación. Se recomienda revisar los
            informes generados antes de comunicar cualquier nota al alumnado.
          </p>
        </div>
      </section>
    </div>
  );
}
