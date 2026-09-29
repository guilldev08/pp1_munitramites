"""Capa de servicios: logica de negocio reutilizable. >>> ACÁ VIVE LA LÓGICA <<<

Las vistas (`views/`) solo coordinan request → servicio → template.
Los servicios no conocen HTTP ni templates: se pueden llamar desde una
vista, desde un management command, desde un test o desde una tarea.

    services/chatbot/   asistente virtual (RAG: indexar → recuperar → generar)

Para AGREGAR UN SERVICIO:
  1. creá la carpeta con su `__init__.py`,
  2. documentá arriba qué problema resuelve,
  3. importalo desde la vista que lo necesita.
"""
