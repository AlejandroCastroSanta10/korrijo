# Rúbrica de corrección — Examen de Seguridad en el Diseño de Software

**Puntuación máxima del examen: 10 puntos.**

Esta rúbrica está organizada por ítems. Cada ítem recoge varias categorías de
calidad y, junto a cada una, la puntuación exacta que el sistema debe asignar
cuando la respuesta del alumno encaje en ella. La puntuación de un ítem es
siempre uno de los valores indicados (no se reparten valores intermedios).

Las respuestas de los ítems de medio punto pueden ser breves: si el concepto es
correcto, no se penaliza por falta de desarrollo.

---

## Ítem 1 — Principio de mínimo privilegio (máx. 0,5 puntos)

- **Bien (0,5 p):** Define el principio correctamente, es decir, otorgar a cada componente, usuario o proceso solo los permisos estrictamente necesarios.
- **Regular (0,25 p):** Transmite la idea de restringir o limitar permisos pero sin una definición precisa.
- **Mal (0 p):** No responde o la definición es incorrecta.

## Ítem 2 — Inyección SQL: definición, explotación y prevención (máx. 2 puntos)

- **Bien (2 p):** Explica qué es la inyección SQL, menciona las consultas parametrizadas como medida de prevención y añade además cómo se explota o alguna otra medida.
- **Notable (1,5 p):** Explica qué es a grandes rasgos y menciona las consultas parametrizadas.
- **Regular (1 p):** Menciona las consultas parametrizadas u otra medida de prevención válida, aunque la explicación del ataque sea pobre o falte.
- **Mal (0 p):** No responde o no menciona ninguna medida de prevención válida.

## Ítem 3 — Autenticación vs. autorización (máx. 0,5 puntos)

- **Bien (0,5 p):** Diferencia ambos conceptos (autenticación = quién eres; autorización = qué puedes hacer).
- **Regular (0,25 p):** Intuye la diferencia pero la expresa de forma imprecisa o confusa.
- **Mal (0 p):** No responde o confunde ambos conceptos.

## Ítem 4 — Modelado de amenazas: definición y fase (máx. 1 punto)

- **Bien (1 p):** Define el modelado de amenazas e indica que se realiza en la fase de diseño.
- **Regular (0,5 p):** Define correctamente sin precisar la fase, o indica la fase con una definición algo vaga.
- **Mal (0 p):** No responde o la descripción es incorrecta.

## Ítem 5 — Defensa en profundidad: definición y ejemplos (máx. 2 puntos)

- **Bien (2 p):** Define la estrategia (múltiples capas de seguridad independientes) y aporta al menos dos ejemplos de capas.
- **Notable (1,5 p):** Define correctamente y aporta uno o dos ejemplos.
- **Regular (1 p):** Transmite la idea de capas o aporta algún ejemplo válido, aunque sin una definición precisa.
- **Mal (0 p):** No responde o la definición es incorrecta y no aporta ejemplos.

## Ítem 6 — OWASP Top 10: definición y utilidad (máx. 1 punto)

- **Bien (1 p):** Explica qué es (lista de los riesgos más críticos en aplicaciones web) e indica para qué sirve.
- **Regular (0,5 p):** Explica qué es correctamente aunque la utilidad sea genérica, o lo menciona como referencia de seguridad sin precisar más.
- **Mal (0 p):** No responde o la descripción es incorrecta.

## Ítem 7 — Cross-Site Scripting (XSS): definición, impacto y mitigación (máx. 2 puntos)

- **Bien (2 p):** Define qué es XSS, menciona algún impacto y al menos dos técnicas de mitigación.
- **Notable (1,5 p):** Define correctamente y menciona al menos una técnica de mitigación junto con algún impacto.
- **Regular (1 p):** Transmite la idea de XSS aunque mencione una sola contramedida o el impacto sea vago.
- **Mal (0 p):** No responde o no menciona ninguna técnica de mitigación.

## Ítem 8 — Cifrado en tránsito vs. cifrado en reposo (máx. 1 punto)

- **Bien (1 p):** Diferencia ambos conceptos (datos en transmisión vs. datos almacenados) e indica que cubren amenazas distintas.
- **Regular (0,5 p):** Diferencia ambos conceptos pero la formulación es imprecisa o no justifica por qué ambos son necesarios.
- **Mal (0 p):** No responde o confunde ambos conceptos.
