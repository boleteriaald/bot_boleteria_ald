# Reconocimiento de anuncios en el agente de ChatLevel

Cómo sabe el "Asistente de Boletería Ald" de qué anuncio viene cada cliente y
qué hace con ese dato. Esto no es parte del monitor de boletas: documenta la
configuración de la cuenta de ChatLevel para que quede versionada.

## De dónde sale el dato

ChatLevel ya guarda la atribución de los anuncios de Meta sin que haya que
programar nada. Cuando alguien entra por un anuncio Click-to-WhatsApp o por un
anuncio de Instagram/Messenger, el contacto queda con estos campos:

| Campo (clave) | Ejemplo | Qué es |
|---|---|---|
| `user_source` | `Ads` | Vacío si el contacto llegó por su cuenta |
| `last_ad` | `120253752457930471` | **ID del anuncio**: es el identificador que importa |
| `last_ad_source_url` | `https://www.instagram.com/p/DdDVjxIgr1D/` | La publicación del anuncio |
| `last_ad_source_platform` | `ad` | Tipo de origen |
| `last_ctwa` | `AfgUlSmG…` | ID del clic en Click-to-WhatsApp |
| `last_campaign_id`, `last_adset_id`, `last_adgroup_id` | (vacíos) | Meta no los envía en este canal |

Los campos de **nombre** del anuncio, de la campaña y del conjunto existen en la
plataforma pero **llegan vacíos**: Meta no manda el nombre en el referral de
WhatsApp. Por eso la traducción de ID a evento se mantiene a mano.

## Cómo está cableado

1. **Nodo `Agente` del flujo "Asistente de Boletería Ald - Inbox"**: el campo
   *mensaje* del nodo ya no manda solo el texto del cliente, sino esto:

   ```
   [ORIGEN DEL CONTACTO — datos internos del sistema, no es lo que escribió el cliente]
   Fuente: {{contact.field.user_source}}
   Anuncio (ID): {{contact.field.last_ad}}
   Publicación del anuncio: {{contact.field.last_ad_source_url}}
   [FIN ORIGEN — si estos tres van vacíos, el contacto es orgánico]

   [MENSAJE DEL CLIENTE]
   {{payload.message.text}} {{vars.vision.text}} {{vars.transcription.text}}
   ```

   Así el agente ve el origen desde el **primer** mensaje, que es cuando sirve.

2. **Instrucciones del agente**: sección *"De qué anuncio viene el cliente"* con
   las reglas de comportamiento y la tabla `ID de anuncio → evento`. Va en las
   instrucciones y no en un documento de conocimiento a propósito: las
   instrucciones están siempre en contexto, mientras que un documento depende de
   que la búsqueda lo recupere (y buscar por un ID de 18 dígitos es justo lo que
   peor le sale). Además el agente ya tiene los 5 documentos que permite el plan.

3. **Campos visibles en la bandeja**: se activaron *Origen del contacto*,
   *Último anuncio (ID)* y *URL de la publicación del anuncio*, para que el
   equipo vea de qué anuncio viene cada conversación y pueda mantener la tabla.

## Cómo se comporta el agente

- **Anuncio en la tabla** → no pregunta qué evento busca: lo confirma en una
  línea y arranca en el paso 2 del flujo de venta (localidades y precios).
- **Anuncio que no está en la tabla** → sabe que viene de una publicación
  nuestra, pero no adivina el evento: lo pregunta.
- **Sin origen** → contacto orgánico, flujo de venta normal desde el paso 1.
- **Lo que dice el cliente manda sobre el anuncio.** Si llega por el anuncio de
  WWE y pregunta por Ryan Castro, se atiende Ryan Castro.
- Nunca menciona IDs, enlaces ni "vi que hiciste clic": confirma el evento, no
  el clic. Y el inventario sigue mandando sobre precios y disponibilidad.

## Cómo agregar un anuncio nuevo

1. Abrir en la bandeja un contacto que haya llegado por ese anuncio y copiar el
   valor de **Último anuncio (ID)**.
2. Agregar una línea a la tabla, en las instrucciones del agente:
   `- <ID> → <evento> (SKU <SKU>)`.
3. Borrar las líneas de eventos que ya pasaron: un anuncio viejo mapeado a un
   evento que ya no se vende hace que el agente confirme algo inexistente.

Contactos con `Fuente: Ads` y un ID que no esté en la tabla son la señal de que
hay un anuncio nuevo sin registrar.

## Tabla actual

| ID del anuncio | Publicación | Evento |
|---|---|---|
| `120253752457930471` | instagram.com/p/DdDVjxIgr1D | WWE — Bogotá, 10 de septiembre (WWE-BOG) |
| `120253753631330471` | instagram.com/p/DdDWSGsgauQ | WWE — Bogotá, 10 de septiembre (WWE-BOG) |

Se dedujeron de los contactos reales: todos los que entraron por esos dos
anuncios preguntaron por WWE. Los anuncios de Arcángel
(`120253266498060471` y compañía) se dejaron fuera porque ese evento ya pasó y
no está en el inventario.
