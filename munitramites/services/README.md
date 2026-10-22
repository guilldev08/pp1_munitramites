# `services/` — lógica que no depende del request

Dos paquetes, ordenados por las etapas que ejecutan. Las vistas y los
management commands son cáscaras finas sobre esto.

## `chatbot/` — asistente RAG

| Archivo | Etapa / qué hace |
|---|---|
| `indexar.py` | 1 · convierte cada trámite activo en fragmentos y los mantiene en memoria (se invalida solo con las señales de `apps.py`) |
| `recuperacion.py` | 2 · BM25 + sinónimos + stopwords; filtra bajo `CHATBOT_UMBRAL` |
| `generacion.py` | 3 · plantilla local (y corte de montos); el modelo redacta con o sin contexto, solo sobre trámites |
| `pipeline.py` | orquesta: saludos, seguimientos, umbral, fuentes y `usar_llm` |
| `llm/prompt.py` | **la ventana de contexto**: `SYSTEM` + `armar_user()` |
| `llm/groq.py` | POST a Groq (API compatible con OpenAI) |
| `llm/__init__.py` | `activo()`, `redactar()`, cooldown y fallback |

Para revisar el contexto exacto que se manda al modelo, sin gastar la API:

```powershell
docker compose exec web python manage.py ver_contexto "¿qué necesito para renovar el DNI?"
```

El chat (con sesión) usa el modelo para redactar con o sin contexto,
siempre dentro de los trámites; si la pregunta es de otro tema, redirige
en una oración. La barra de búsqueda pública, sin sesión, responde con
plantillas para no gastar la API.

## `scraper/` — importación de trámites oficiales

| Archivo | Etapa / qué hace |
|---|---|
| `planilla.py` | 1 · lee `data/organismos_misiones.csv` y crea los organismos |
| `busqueda/vocabulario.py` | palabras del dominio (temas, puertas, sinónimos) |
| `busqueda/relevancia.py` | 2 · puntúa cada link: trámite, puerta o ruido |
| `busqueda/rastreo.py` | 2 · HTTP, candidatos y puertas |
| `fichas/extraccion.py` | 3 · título, descripción, requisitos y enlaces de la ficha |
| `fichas/clasificacion.py` | 3 · tema, municipio y modalidad |
| `servicio.py` | orquesta el scraping; todo queda inactivo para revisar |

Todo lo que sale del scraper queda **inactivo** hasta publicarlo desde el
Centro de Trámites.
