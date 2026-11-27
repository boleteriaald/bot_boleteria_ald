# Don Omar 2027 — localidades por evento

Leídas del catálogo de Ticketmaster el 26-nov-2026 (~18:50), uniendo las páginas de venta
general y de preventa. Los nombres van tal cual los escribe la página, con sus espacios dobles.

Al filtrar no importan mayúsculas, tildes, guiones ni espacios dobles. La palabra del filtro
basta con que esté **contenida** en el nombre.

## Bogotá — 4 de noviembre (Vive Claro)

Venta general: <https://www.ticketmaster.co/event/don-omar-bogota-venta-general>
(26-nov: AGOTADO; ya está en el monitor y en la reserva)

| Tipo | Nombre en la página | Palabra para filtrar |
|---|---|---|
| Numerada | `101 - 103 - 105 - 107  (Mayores +18)` | `101` |
| Numerada | `102 - 104 - 106 -108 (Mayores +18)` | `102` |
| Numerada | `109 - 111 - 113 - 115 (Mayores +18)` | `109` |
| Numerada | `110 - 112 - 114 - 116 (Mayores +18)` | `110` |
| Numerada | `117 - 119 - 121 - 123 (Mayores +18)` | `117` |
| Numerada | `118 - 120 - 122 - 124 (Mayores +18)` | `118` |
| Numerada | `125 - 127 - 129 - 131 (Mayores +18)` | `125` |
| Numerada | `126 - 128 - 130 - 132 (Mayores +18)` | `126` |
| VIP | `Kingdom VIP 1` | `kingdom vip 1` |
| VIP | `Kingdom VIP 2` | `kingdom vip 2` |
| Palco | `Palco Platino - Occidental (Mayores +18)` | |
| Palco | `Palco Platino - Oriental (Mayores +18)` | |
| Palco | `Palco Rubi - Occidental (Mayores +18)` | |
| Palco | `Palco Rubi - Oriental (Mayores +18)` | |
| Palco | `Palco Plata - Occidental (Mayores +18)` | |
| Palco | `Palco Plata - Oriental (Mayores +18)` | |
| Palco | `Palco Bronce - Occidental (Mayores +18)` | |
| Palco | `Palco Bronce - Oriental (Mayores +18)` | |

Los términos y condiciones nombran además Palco Diamante y Palco Oro: no salen en el catálogo.

## Cali — 5 de noviembre (Pascual Guerrero)

Venta general: <https://www.ticketmaster.co/event/don-omar-cali-venta-general>

| Tipo | Nombre en la página | Palabra para filtrar |
|---|---|---|
| Grada | `Oriental - Alta (Mayores + 18)` | `oriental alta` |
| Grada | `Oriental - Baja (Mayores +18)` | `oriental baja` |
| VIP | `Kingdom - VIP 1 Occidental (Mayores +18)` | `kingdom vip 1` |
| VIP | `Kingdom - VIP 2 Oriental (Mayores + 18)` | `kingdom vip 2` |
| Palco | `Palcos Diamante x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Diamante x 10 - Oriental (Mayores + 18)` | |
| Palco | `Palcos Platino x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Platino x 10 - Oriental (Mayores +18)` | |
| Palco | `Palcos Oro x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Oro x 10 - Oriental (Mayores + 18)` | |
| Palco | `Palcos Rubí  x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Rubí  x 10 - Oriental (Mayores + 18)` | |
| Palco | `Palcos Plata  x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Plata  x 10 - Oriental (Mayores + 18)` | |
| Palco | `Palcos Bronce  x 10 - Occidental (Mayores + 18)` | |
| Palco | `Palcos Bronce  x 10 - Oriental (Mayores + 18)` | |

Los términos nombran además **Occidental Alta, Occidental Media, Occidental Baja y Norte**: no
han salido en el catálogo, así que su nombre exacto no se conoce. Probable: `occidental alta`,
`occidental media`, `occidental baja`, `norte`.

## Medellín — 6 y 7 de noviembre (Polideportivo Sur, Envigado)

- 6 de noviembre: <https://www.ticketmaster.co/event/don-omar-medellin-venta-general-fecha-2>
- 7 de noviembre: <https://www.ticketmaster.co/event/don-omar-medellin-venta-general>

Las dos fechas usan los mismos nombres.

| Tipo | Nombre en la página | Palabra para filtrar |
|---|---|---|
| Grada | `Occidental` | `occidental` |
| Grada | `Norte` | `norte` |
| Grada | `Sur` | `sur` |
| VIP | `KINGDOM VIP 1` | `kingdom vip 1` |
| VIP | `KINGDOM VIP 2` | `kingdom vip 2` |
| Palco | `Palco Diamante Norte` | |
| Palco | `Palco Diamante Sur` | |
| Palco | `Palco Platino Norte` | |
| Palco | `Palco Platino Sur` | |
| Palco | `Palco Oro Norte` | |
| Palco | `Palco Oro Sur` | |

En la venta general del 7 solo aparecen hoy palcos Platino y Diamante y los Kingdom; las
agotadas desaparecen del catálogo. En la del 6 hoy no aparece `Occidental`.

## Cómo usar los filtros

- **Hoy no hace falta filtrar:** las URLs del monitor excluyen `palco`, así que si reabre
  cualquier grada, numerada o VIP, avisa y reserva. La preventa de Bogotá excluye además
  `101 - 103 - 105 - 107`.
- En `monitor_todas_las_urls.py`, `FILTROS_LOCALIDADES` ya tiene un bloque comentado por URL con
  todas las localidades.
- **Para quedarse solo con algunas**, deja la exclusión de palcos puesta: `norte` y `sur` también
  están contenidas en "Palco Platino Norte" y "Palco Oro Sur".
- Avisos, en `FILTROS_LOCALIDADES` (ejemplo Medellín 7):

  ```python
  "https://www.ticketmaster.co/event/don-omar-medellin-venta-general":
      ["occidental", "norte", "sur"],
  ```

- Reserva, en `RESERVAR_TICKETMASTER` (el orden de `sectores` es la prioridad):

  ```python
  "https://www.ticketmaster.co/event/don-omar-medellin-venta-general":
      {"maximo": 4, "max_reservas": 8, "excluir": ["palco"],
       "sectores": ["occidental", "sur", "norte"]},
  ```

- No hace falta borrar `estado_notificaciones.json` para que una reapertura cuente: una localidad
  que desaparece 3 lecturas seguidas se olvida y, al volver, es nueva.
