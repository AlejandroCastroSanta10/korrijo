# Examen modelo — "Fundamentos de redes"

## Pregunta 1 (3 p) — ¿Qué es el protocolo TCP y en qué se diferencia de UDP?

TCP es un protocolo de transporte **orientado a conexión** que garantiza la entrega fiable
y ordenada de los datos: usa confirmaciones (ACK) y retransmite los paquetes perdidos. UDP,
en cambio, es **no orientado a conexión**: no garantiza la entrega ni el orden, pero es más
rápido y con menos sobrecarga. TCP es adecuado para web y correo; UDP para streaming,
videojuegos o VoIP.

## Pregunta 2 (4 p) — Explica qué es una dirección IP y distingue entre IPv4 e IPv6.

Una dirección IP identifica de forma única a un dispositivo dentro de una red. **IPv4** usa
**32 bits** en notación decimal con puntos (p. ej. `192.168.1.1`), con un espacio de unos
**4.300 millones** de direcciones (2^32). **IPv6** usa **128 bits** en notación hexadecimal
y se creó para resolver el agotamiento de direcciones de IPv4, ofreciendo un espacio
muchísimo mayor (2^128).

## Pregunta 3 (3 p) — ¿Qué es el modelo OSI y cuántas capas tiene?

El modelo OSI es un estándar que organiza la comunicación en red en **7 capas**:
**Física, Enlace de datos, Red, Transporte, Sesión, Presentación y Aplicación.** Cada capa
cumple una función específica y se comunica con las capas adyacentes, lo que facilita la
interoperabilidad entre sistemas.
