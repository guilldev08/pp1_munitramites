# Munitramites

![Captura de la página pública de Munitramites](docs/img/captura-pagina-publica.png)

## ¿Qué es?

Munitramites es una página web que reúne la información de los trámites
públicos de la provincia de Misiones. En vez de preguntar por teléfono o ir
hasta una oficina solo para saber qué papeles hacen falta, acá está todo
junto: qué se necesita, dónde se hace y con qué organismo hay que hablar.

## ¿Qué hace?

- **Busca trámites.** Se puede filtrar por tema, municipio o modalidad
  (presencial, digital o mixta) y ver una ficha con los requisitos, el
  organismo responsable y los enlaces oficiales.
- **Contesta preguntas.** Tiene un asistente que responde con la información
  de los trámites cargados y dice de qué trámite sacó la respuesta. Si no
  sabe, lo aclara en lugar de inventar.
- **Recibe consultas.** Cualquier persona puede crear una cuenta, mandar una
  consulta, una sugerencia o un reclamo, y seguir la respuesta.
- **Administra el contenido.** Las cuentas del sitio que tienen permiso entran
  a un panel privado para cargar y editar trámites, crear temas y responder
  las consultas que llegan.

## ¿Para qué sirve?

Para que la gente pierda menos tiempo y menos viajes: toda la información de
un trámite está en un solo lugar, actualizada y explicada en lenguaje simple.
Del otro lado, le da al organismo una sola herramienta para publicar los
trámites y atender lo que la gente pregunta.

## Cómo ejecutarla

Solo hace falta tener [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado y abierto. No hay que instalar Python ni bases de datos: todo corre
dentro de Docker.

```powershell
git clone https://github.com/guilldev08/pp1_munitramites.git
cd pp1_munitramites
git switch feature/frontend
docker compose up -d --build
```

La primera vez tarda unos minutos porque arma el entorno. Cuando termina,
la página queda disponible en:

**http://localhost:8000/**

### Primer arranque

La base empieza vacía. Para cargar los trámites de ejemplo y crear la cuenta
de administrador:

```powershell
docker compose exec web python manage.py cargar_datos
docker compose exec web python manage.py createsuperuser
```

Después se entra con esa cuenta y se puede ver el panel de administración en
**http://localhost:8000/panel/**.

### Para apagarla

```powershell
docker compose down
```

## ¿Qué se puede visitar?

| Dirección | Qué hay |
|---|---|
| http://localhost:8000/ | Página de inicio |
| http://localhost:8000/tramites/ | Buscador de trámites |
| http://localhost:8000/chatbot/ | Asistente virtual |
| http://localhost:8000/panel/ | Panel de administración (pide iniciar sesión) |
