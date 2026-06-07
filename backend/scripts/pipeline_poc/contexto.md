# Contexto — Temario de "Fundamentos de redes"
.
## 1. Protocolos de transporte: TCP y UDP

- **TCP (Transmission Control Protocol):** protocolo *orientado a conexión*. Establece la
  conexión (handshake) y garantiza la entrega ordenada y fiable de los datos mediante
  confirmaciones (ACK) y retransmisión de los paquetes perdidos. Tiene más sobrecarga.
  Usos típicos: web (HTTP/HTTPS), correo electrónico, transferencia de ficheros.
- **UDP (User Datagram Protocol):** protocolo *no orientado a conexión*. No garantiza la
  entrega ni el orden, pero es más rápido y ligero. Usos típicos: streaming de audio/vídeo,
  videojuegos en línea, DNS, VoIP.

## 2. Direccionamiento IP

- Una **dirección IP** identifica de forma única a un dispositivo dentro de una red.
- **IPv4:** direcciones de **32 bits**, escritas en notación decimal con puntos
  (p. ej. `192.168.1.1`). El espacio de direcciones es de 2^32, es decir, unos
  **4.300 millones** de direcciones, hoy prácticamente agotadas.
- **IPv6:** direcciones de **128 bits**, escritas en notación hexadecimal separada por
  dos puntos. Se creó para resolver el agotamiento de IPv4 y ofrece un espacio
  enormemente mayor (2^128).

## 3. Modelo OSI

- El **modelo OSI** (Open Systems Interconnection) es un estándar que organiza la
  comunicación en red en **7 capas**, cada una con una función específica que se apoya en
  la inferior y da servicio a la superior.
- Capas, de la 1 a la 7: **Física, Enlace de datos, Red, Transporte, Sesión,
  Presentación y Aplicación.**
