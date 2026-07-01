"""Genera un PDF con las correcciones de referencia del dataset de evaluación.

Son las notas asignadas manualmente (ítem por ítem, siguiendo cada rúbrica) que
sirven de referencia para el MAE en la evaluación de los modelos textuales.
Propuestas para que el autor las revise, ajuste y haga suyas.

Uso (desde backend/, con el entorno activado):
    python scripts/gen_correcciones_referencia.py
    python scripts/gen_correcciones_referencia.py --out ../docs/dataset-korrijo/correcciones_referencia.pdf
"""

import argparse
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DEFAULT_OUT = (
    Path(__file__).resolve().parents[2]
    / "docs" / "dataset-korrijo" / "correcciones_referencia.pdf"
)

# Cada examen: metadatos + lista de (criterio, máx, asignada, justificación).
CORRECCIONES = [
    {
        "prueba": "Prueba 1 — Historia: La Prehistoria",
        "alumno": "María Pérez Molina",
        "perfil": "Perfil fuerte",
        "escala": "/ 10",
        "nota": "7,25 / 10",
        "items": [
            ("1. Vida nómada (Paleolítico)", "2", "1,5", "Detalla caza, pesca y recolección y el utillaje del grupo, pero no explica cómo la búsqueda de recursos obligaba a desplazarse, que es parte central de la pregunta."),
            ("2. Agricultura y sedentarismo", "1,25", "1,0", "Vincula la producción de alimento con el sedentarismo, aunque de forma breve y sin definir qué es la agricultura."),
            ("3. Ganadería y sedentarismo", "1,25", "0,5", "Nombra la ganadería junto a la agricultura pero no explica qué aportó ni cómo complementó al cultivo."),
            ("4. Edad del Cobre", "1", "1,0", "Identifica el cobre como inicio de la metalurgia y señala su maleabilidad."),
            ("5. Edad del Bronce", "1,25", "1,25", "Correcto: aleación de cobre y estaño, más resistente y con mejores armas."),
            ("6. Edad del Hierro", "1,25", "0,5", "Solo dice que permitió civilizaciones más complejas; no menciona que el hierro es más abundante/duro ni su impacto en herramientas."),
            ("7. Fin de la Prehistoria", "0,5", "0,5", "Identifica la escritura como hito que cierra la Prehistoria."),
            ("8. Impacto de la escritura", "1,5", "1,0", "Cita el registro de acontecimientos y de la economía, pero el análisis del impacto social queda genérico."),
        ],
    },
    {
        "prueba": "Prueba 1 — Historia: La Prehistoria",
        "alumno": "Aitana Rojas Castillo",
        "perfil": "Perfil flojo",
        "escala": "/ 10",
        "nota": "5,25 / 10",
        "items": [
            ("1. Vida nómada (Paleolítico)", "2", "1,25", "Recoge el nomadismo, la caza/recolección y el desplazamiento al agotarse los recursos, pero omite la pesca y es escueta."),
            ("2. Agricultura y sedentarismo", "1,25", "1,25", "Explica bien qué es la agricultura y su relación con el sedentarismo."),
            ("3. Ganadería y sedentarismo", "1,25", "0,25", "'Tenían algunos animales': menciona la ganadería de pasada, sin explicar su aporte."),
            ("4. Edad del Cobre", "1", "0,25", "Nombra el cobre como primer metal pero no indica ninguna característica ni ventaja."),
            ("5. Edad del Bronce", "1,25", "0,75", "Dice que el bronce es una mezcla de metales más resistente para armas, sin concretar cobre+estaño."),
            ("6. Edad del Hierro", "1,25", "0,75", "Indica que el hierro es el más fuerte y su uso, pero no que fuera más abundante."),
            ("7. Fin de la Prehistoria", "0,5", "0,5", "Identifica la escritura como hito que cierra la Prehistoria."),
            ("8. Impacto de la escritura", "1,5", "0,25", "Impacto muy superficial ('escribir cosas y guardarlas para que no se olviden')."),
        ],
    },
    {
        "prueba": "Prueba 2 — Auxiliar de Enfermería",
        "alumno": "Isabel Santa Sánchez",
        "perfil": "Perfil flojo",
        "escala": "/ 100",
        "nota": "61,75 / 100  (6,18 / 10)",
        "items": [
            ("1. Riñón y desecho nitrogenado", "4", "2,8", "Nombra la urea pero la función renal es imprecisa ('excretar orina'), sin filtración/regulación. [Parcial]"),
            ("2. Úlcera por presión", "5", "5,0", "Define la UPP e incluye el sacro entre las zonas. [Completo]"),
            ("3. 5 momentos lavado de manos", "6", "0,0", "Los momentos indicados no se corresponden con los 5 de la OMS. [Incorrecto]"),
            ("4. Subcutánea vs. intramuscular", "5", "3,5", "Diferencia el tejido pero omite la absorción. [Parcial]"),
            ("5. Maniobra de Heimlich", "6", "4,2", "Indica la situación (atragantamiento) pero no describe la técnica. [Parcial]"),
            ("6. Balance hídrico", "5", "5,0", "Define el balance hídrico y explica el cálculo (entradas − salidas). [Completo]"),
            ("7. Presión arterial normal", "4", "2,8", "Indica 120/80 pero no el umbral de hipertensión. [Parcial]"),
            ("8. Esterilización vs. desinfección", "5", "5,0", "Diferencia ambos conceptos correctamente. [Completo]"),
            ("9. Medicación oral y disfagia", "6", "4,2", "Menciona valorar la deglución, sin una actuación concreta adicional. [Parcial]"),
            ("10. Relación compresión-ventilación", "6", "0,0", "Ratio '100-1' incorrecto (es 30:2). [Incorrecto]"),
            ("11. Sonda nasogástrica", "4", "2,8", "Define la SNG y menciona un uso (alimentación). [Parcial]"),
            ("12. Signos vitales", "5", "5,0", "Enumera los signos vitales con valores correctos. [Completo]"),
            ("13. Precauciones TBC activa", "5", "1,75", "Solo la mascarilla; faltan aislamiento y notificación. [Incompleto]"),
            ("14. Escala de Glasgow", "5", "1,75", "Indica el uso pero no describe la escala. [Incompleto]"),
            ("15. Efecto adverso vs. secundario", "4", "1,4", "Confunde el efecto adverso ('un error'); el secundario queda a medias. [Incompleto]"),
            ("16. Hemorragia externa", "6", "2,1", "Menciona hemostasia/torniquete pero no la compresión directa ni pasos intermedios. [Incompleto · borderline]"),
            ("17. Movilización pasiva", "4", "4,0", "Define la movilización pasiva e indica pacientes encamados. [Completo]"),
            ("18. Insulina y déficit", "4", "4,0", "Función (transporte de glucosa) y consecuencia del déficit (diabetes). [Completo]"),
            ("19. Guantes estériles vs. generales", "4", "4,0", "Diferencia ambos tipos con ejemplos. [Completo]"),
            ("20. Hipoglucemia", "7", "2,45", "Cita síntomas pero no la primera actuación. [Incompleto]"),
        ],
    },
    {
        "prueba": "Prueba 2 — Auxiliar de Enfermería",
        "alumno": "Joana Albert Verdú",
        "perfil": "Perfil fuerte",
        "escala": "/ 100",
        "nota": "73,7 / 100  (7,37 / 10)",
        "items": [
            ("1. Riñón y desecho nitrogenado", "4", "4,0", "Filtración de la sangre y urea (menciona también creatinina). [Completo]"),
            ("2. Úlcera por presión", "5", "5,0", "Define la UPP (presión/isquemia) e incluye el sacro. [Completo]"),
            ("3. 5 momentos lavado de manos", "6", "4,2", "Cuatro momentos correctos; falta el de riesgo de exposición a fluidos. [Parcial]"),
            ("4. Subcutánea vs. intramuscular", "5", "3,5", "Diferencia profundidad/tejido pero omite la absorción. [Parcial]"),
            ("5. Maniobra de Heimlich", "6", "6,0", "Indica la situación y describe correctamente la técnica. [Completo]"),
            ("6. Balance hídrico", "5", "5,0", "Define el balance hídrico y su cálculo en 24 h. [Completo]"),
            ("7. Presión arterial normal", "4", "1,4", "Da rangos confusos y no indica claramente 120/80. [Incompleto]"),
            ("8. Esterilización vs. desinfección", "5", "5,0", "Diferencia esterilización (incluye esporas) y desinfección. [Completo]"),
            ("9. Medicación oral y disfagia", "6", "4,2", "Da medidas prácticas (Fowler, triturar) pero sin valorar el riesgo de aspiración/restricciones. [Parcial · borderline]"),
            ("10. Relación compresión-ventilación", "6", "4,2", "Indica 30:2 (correcto) aunque añade un ratio erróneo y omite profundidad/frecuencia. [Parcial · borderline]"),
            ("11. Sonda nasogástrica", "4", "4,0", "Define la SNG y varios usos. [Completo]"),
            ("12. Signos vitales", "5", "5,0", "Enumera los signos vitales con valores esencialmente correctos. [Completo]"),
            ("13. Precauciones TBC activa", "5", "1,75", "Solo 'aislamiento estricto'; faltan medidas concretas. [Incompleto]"),
            ("14. Escala de Glasgow", "5", "1,75", "Indica el uso pero no describe la escala. [Incompleto]"),
            ("15. Efecto adverso vs. secundario", "4", "1,4", "Solo aborda el efecto secundario y de forma imprecisa. [Incompleto]"),
            ("16. Hemorragia externa", "6", "4,2", "Compresión directa y no retirar el apósito; faltan elevar/compresión proximal. [Parcial]"),
            ("17. Movilización pasiva", "4", "4,0", "Define la movilización pasiva e indica pacientes encamados. [Completo]"),
            ("18. Insulina y déficit", "4", "2,8", "Da la consecuencia del déficit pero la función es imprecisa. [Parcial · borderline]"),
            ("19. Guantes estériles vs. generales", "4", "1,4", "Solo describe los guantes estériles. [Incompleto]"),
            ("20. Hipoglucemia", "7", "4,9", "Actuación excelente (dextro, HC, glucagón) pero pocos síntomas (2). [Parcial]"),
        ],
    },
    {
        "prueba": "Prueba 3 — Seguridad en el Diseño de Software",
        "alumno": "Alejandro Castro Santa",
        "perfil": "Perfil fuerte",
        "escala": "/ 10",
        "nota": "9,5 / 10",
        "items": [
            ("1. Mínimo privilegio", "0,5", "0,5", "Define correctamente el principio y su importancia."),
            ("2. Inyección SQL", "2", "1,5", "Explica bien qué es y cómo se explota, y propone validación/saneamiento; se descuenta por no citar las consultas parametrizadas (medida canónica)."),
            ("3. Autenticación vs. autorización", "0,5", "0,5", "Diferencia ambos conceptos."),
            ("4. Modelado de amenazas", "1", "1,0", "Define el modelado de amenazas e indica la fase de diseño."),
            ("5. Defensa en profundidad", "2", "2,0", "Define la estrategia y aporta tres capas de ejemplo."),
            ("6. OWASP Top 10", "1", "1,0", "Explica qué es y para qué sirve."),
            ("7. Cross-Site Scripting (XSS)", "2", "2,0", "Define XSS, su impacto y dos mitigaciones (saneamiento y CSP)."),
            ("8. Cifrado en tránsito vs. reposo", "1", "1,0", "Diferencia ambos y justifica por qué son necesarios."),
        ],
    },
    {
        "prueba": "Prueba 3 — Seguridad en el Diseño de Software",
        "alumno": "Juan Felipe Viñales",
        "perfil": "Perfil flojo",
        "escala": "/ 10",
        "nota": "5,5 / 10",
        "items": [
            ("1. Mínimo privilegio", "0,5", "0,5", "Definición correcta del principio."),
            ("2. Inyección SQL", "2", "1,0", "Idea básica del ataque y menciona la validación como prevención, pero sin consultas parametrizadas ni detalle de la explotación."),
            ("3. Autenticación vs. autorización", "0,5", "0,5", "Diferencia correctamente ambos conceptos."),
            ("4. Modelado de amenazas", "1", "0,5", "Define el modelado de amenazas pero no indica la fase de diseño."),
            ("5. Defensa en profundidad", "2", "1,0", "Transmite la idea de varias capas y da dos ejemplos, pero sin una definición precisa (capas independientes)."),
            ("6. OWASP Top 10", "1", "0,5", "Dice qué es pero no para qué sirve."),
            ("7. Cross-Site Scripting (XSS)", "2", "1,0", "Define XSS con un impacto y una sola contramedida (validación)."),
            ("8. Cifrado en tránsito vs. reposo", "1", "0,5", "Diferencia ambos cifrados pero no justifica que cubren amenazas distintas."),
        ],
    },
]


def construir(out: Path) -> None:
    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle("celda", parent=estilos["Normal"], fontSize=8, leading=10)
    h_prueba = ParagraphStyle("hprueba", parent=estilos["Heading2"], fontSize=12, spaceBefore=6, spaceAfter=2)
    h_alumno = ParagraphStyle("halumno", parent=estilos["Normal"], fontSize=10, spaceAfter=6)

    historia = [
        Paragraph("Correcciones de referencia — dataset de evaluación", estilos["Title"]),
        Paragraph(
            "Notas asignadas manualmente ítem por ítem siguiendo cada rúbrica. "
            "Sirven de referencia (<i>ground truth</i>) para el cálculo del MAE en "
            "la evaluación de los modelos textuales.",
            estilos["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]

    anchos = [48 * mm, 14 * mm, 16 * mm, 102 * mm]
    for exam in CORRECCIONES:
        historia.append(Paragraph(exam["prueba"], h_prueba))
        historia.append(Paragraph(
            f"<b>{exam['alumno']}</b> — {exam['perfil']} · "
            f"Nota de referencia: <b>{exam['nota']}</b>", h_alumno,
        ))

        filas = [[
            Paragraph("<b>Criterio</b>", celda), Paragraph("<b>Máx.</b>", celda),
            Paragraph("<b>Asig.</b>", celda), Paragraph("<b>Justificación</b>", celda),
        ]]
        for criterio, maximo, asignada, justif in exam["items"]:
            filas.append([
                Paragraph(criterio, celda), Paragraph(maximo, celda),
                Paragraph(asignada, celda), Paragraph(justif, celda),
            ])

        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f5f4f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f1")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        historia.append(tabla)
        historia.append(Spacer(1, 6 * mm))

    doc.build(historia)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Ruta del PDF de salida.")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    construir(out)
    print(f"PDF generado en: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
