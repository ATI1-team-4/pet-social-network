# Petly - Red social para mascotas

Plataforma colaborativa para amantes de los animales, desarrollada para la materia **Aplicaciones con Tecnología Internet (Semestre 2026-1)** de la Escuela de Computación de la Universidad Central de Venezuela.

## Sobre el proyecto

Petly conecta a dueños y amantes de los animales para compartir experiencias, buscar adopción responsable, encontrar pareja o socializar a sus mascotas de forma segura.

### Funcionalidades principales
- **Perfiles dobles:** cada usuario maneja su perfil principal de humano y puede registrar múltiples perfiles para sus mascotas asociadas.
- **Muro y multimedia:** publicaciones con fotos, videos, audios y enlaces, con soporte para menciones y comentarios anidados en hilo.
- **Feeds especializados:**
  - *Adopción responsable:* avisos de adopción, postulaciones y transferencia acordada de la mascota al nuevo dueño.
  - *Búsqueda de pareja:* filtro y conexión entre mascotas compatibles.
  - *Socialización:* aprendizaje y convivencia segura para animales domésticos.
- **Comunicación y confianza:** mensajería directa por chat, sistema de reputación para encuentros presenciales y moderación de contenido.

## Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| Lenguaje | Python 3.12+ | Lenguaje base del proyecto |
| Framework web | Django 6.1+ | Backend, ORM y arquitectura web |
| Estilos CSS | Tailwind CSS v4 | Sistema de diseño y utilidades visuales |
| Base de datos | SQLite | Persistencia relacional de datos en volumen Docker |
| Contenedores | Docker y Docker Compose | Estandarización y aislamiento del entorno de desarrollo |
| Recarga en vivo | django-browser-reload | Refresco automático del navegador ante cambios en plantillas y estilos |
| Control de versiones | Git y GitHub | Repositorio y control de versiones |
| Gestión del proyecto | GitHub Projects | Tablero Kanban y trazabilidad de issues |

## Puesta en marcha

### Opción recomendada: Docker y Docker Compose

> [!TIP]
> **Recomendación para usuarios de Windows:**
> Es preferible ejecutar el proyecto dentro de un entorno **WSL 2 (Windows Subsystem for Linux)** junto con **Docker Desktop** (con la integración de WSL activada en *Settings > Resources > WSL integration*). Para obtener el máximo rendimiento de lectura/escritura y detección inmediata de cambios en caliente, asegúrate de clonar y abrir el proyecto dentro del sistema de archivos nativo de Linux (por ejemplo en `~/development/...` o `/home/<usuario>/...`) y **no** en rutas montadas de Windows (`/mnt/c/...`).

#### 1. Iniciar los contenedores

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone https://github.com/ATI1-team-4/pet-social-network.git
cd pet-social-network

# 2. Construir las imágenes y levantar los servicios en segundo plano
docker compose up -d --build

# 3. Aplicar las migraciones iniciales de base de datos dentro del contenedor
docker compose exec web python manage.py migrate
```

La aplicación estará lista y accesible en [http://localhost:8000/](http://localhost:8000/).

---

### Recarga automática en el navegador (Live Reload)

El entorno de desarrollo incluye recarga automática en vivo mediante **`django-browser-reload`** y el compilador continuo de **Tailwind CSS v4**:
- Al modificar y guardar cualquier archivo de plantilla HTML (`.html`), hoja de estilos (`.css`) o vista de Python (`.py`), **la pestaña de tu navegador se recarga sola de forma inmediata**, sin necesidad de presionar `F5`.
- Tailwind CSS se ejecuta en segundo plano dentro del contenedor `petly_web` y recompila las nuevas clases en ~150 ms.
- Esta funcionalidad está condicionada exclusivamente a `DEBUG=True` en [config/settings.py](config/settings.py) y [config/urls.py](config/urls.py), por lo que se desactiva por completo en producción sin generar sobrecarga.

---

### Gestión e instalación de dependencias en Docker

Para garantizar que todos los desarrolladores mantengan exactamente las mismas librerías y evitar discrepancias entre el entorno local y el contenedor, la instalación de dependencias debe realizarse dentro del contenedor y luego versionarse en `requirements.txt`:

```bash
# Opción A: Entrar a la terminal interactiva del contenedor web
docker compose exec web bash
pip install <nombre-del-paquete>
pip freeze > requirements.txt
exit

# Opción B: Instalar directamente desde la terminal anfitriona
docker compose exec web pip install <nombre-del-paquete>
# Luego agrega el paquete con su versión exacta a requirements.txt
```

> [!IMPORTANT]
> Cada vez que agregues o actualices librerías en `requirements.txt`, ejecuta `docker compose up -d --build` para reconstruir la imagen y asegurar que todo el equipo trabaje con las dependencias actualizadas.

---

### Comandos frecuentes de Docker

| Acción | Comando |
| :--- | :--- |
| Iniciar contenedores en segundo plano | `docker compose up -d` |
| Reconstruir e iniciar contenedores | `docker compose up -d --build` |
| Ver logs en vivo de Django y Tailwind | `docker compose logs -f web` |
| Ver logs en vivo de la base de datos | `docker compose logs -f db` |
| Ejecutar las pruebas unitarias | `docker compose exec web python manage.py test` |
| Crear un superusuario administrador | `docker compose exec web python manage.py createsuperuser` |
| Detener los contenedores | `docker compose down` |

---

### Opción alternativa: Entorno virtual local (.venv)

Si prefieres ejecutar el proyecto directamente en tu máquina sin Docker:

```bash
# 1. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones
python manage.py migrate

# 4. Iniciar el servidor
python manage.py runserver
```

### Variables de entorno (`.env.dev`)

El proyecto incluye el archivo [.env.dev](.env.dev) preconfigurado para desarrollo local con las siguientes variables:

| Variable | Propósito | Valor por defecto |
| :--- | :--- | :--- |
| `SECRET_KEY` | Clave criptográfica para firmas de sesiones y tokens | Clave de desarrollo local |
| `DEBUG` | Modo depuración con mensajes detallados de error | `True` |
| `ALLOWED_HOSTS` | Lista de dominios válidos a los que responde el servidor | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes permitidos para validación segura de formularios POST | `http://localhost:8000,http://127.0.0.1:8000` |
| `SITE_DOMAIN` | Dominio propio para generar enlaces absolutos en correos | `localhost:8000` |
| `SITE_PROTOCOL` | Protocolo de conexión (`http` o `https`) | `http` |
| `DATABASE_DIR` | Carpeta local donde se guarda la base de datos SQLite | `data` |
| `DATABASE_NAME` | Nombre del archivo de base de datos | `db.sqlite3` |

## Estructura del proyecto

El proyecto implementa una arquitectura modular donde las funcionalidades de negocio se agrupan en el subdirectorio `apps/`, manteniendo la raíz despejada y facilitando el trabajo colaborativo entre frontend, backend y base de datos:

```text
pet-social-network/
├── apps/                         # Paquete contenedor de aplicaciones modulares
│   ├── __init__.py
│   └── <module_name>/            # Ejemplo de estructura interna estándar (ej. accounts)
│       ├── admin.py              # Configuración para el panel de administración
│       ├── apps.py               # Configuración de la app (name = 'apps.<module_name>')
│       ├── forms.py              # Formularios y validaciones de entrada
│       ├── models.py             # Modelos de datos del módulo
│       ├── services.py           # Capa de lógica de negocio desacoplada
│       ├── urls.py               # Enrutamiento específico del módulo
│       ├── views.py              # Controladores de vista
│       ├── templates/            # Plantillas aisladas por espacio de nombres
│       │   └── <module_name>/
│       │       └── example.html
│       └── tests/                # Pruebas unitarias del módulo
├── config/                       # Configuración central del proyecto Django
│   ├── settings.py               # Ajustes generales, middleware y apps instaladas
│   ├── urls.py                   # Enrutador principal de la aplicación
│   ├── wsgi.py                   # Punto de entrada WSGI para despliegue tradicional
│   └── asgi.py                   # Punto de entrada ASGI para WebSockets y asincronía
├── media/                        # Archivos multimedia subidos por usuarios (ignorado en Git)
│   ├── avatars/
│   ├── pets/
│   └── posts/
├── static/                       # Recursos estáticos del sistema
│   ├── images/                   # Logotipos, íconos y gráficos estáticos del sistema
│   └── js/                       # Scripts JavaScript del cliente (main.js)
├── templates/                    # Plantillas globales y componentes compartidos
│   ├── base.html                 # Plantilla maestra con estructura HTML5 compartida
│   ├── components/               # Componentes reutilizables (navbar, footer, mensajes)
│   └── layouts/                  # Diseños de página base
├── theme/                        # Aplicación de Tailwind CSS (fuente y compilación de estilos)
│   └── static_src/src/styles.css # Hoja de estilos fuente con tokens y temas personalizados
├── .dockerignore                 # Reglas de exclusión para imágenes Docker
├── .editorconfig                 # Reglas automáticas de formato e indentación
├── .env.dev                      # Variables de entorno para desarrollo local
├── .gitignore                    # Reglas de exclusión de Git
├── Dockerfile                    # Definición de la imagen del contenedor web
├── docker-compose.yml            # Orquestación de servicios (web y base de datos)
├── manage.py                     # Utilidad de línea de comandos de Django
└── requirements.txt              # Dependencias de Python del proyecto
```

> [!NOTE]
> La carpeta `apps/<module_name>/` en este diagrama funciona como **plantilla de referencia arquitectónica** para la creación de futuros módulos. Actualmente, el proyecto cuenta con la aplicación inicial **`apps.core`**, la cual actúa como núcleo del sistema proveyendo modelos base abstractos (`TimeStampedModel` para auditoría temporal), utilidades transversales y la vista de inicio del portal público.

### Principios de la arquitectura modular

| Carpeta | Propósito | Reglas de configuración |
| :--- | :--- | :--- |
| `apps/` | Aloja los dominios del sistema separados en submódulos independientes | Cada app configura su clase en `apps.py` con `name = 'apps.<nombre_app>'` y su enrutador `urls.py` con `app_name = '<nombre_app>'` para la resolución inversa con `{% url %}`. |
| `theme/` | Gestión y compilación del sistema de diseño Tailwind CSS | Contiene la configuración de estilos fuente y genera el paquete CSS unificado en `theme/static/css/dist/styles.css`. |
| `templates/` | Plantilla base global, layouts intermedios y componentes reutilizables | `base.html` es el cascarón raíz. Todo layout dentro de `templates/layouts/` (ej. `app.html`) debe heredar obligatoriamente de `base.html` con `{% extends 'base.html' %}`. Las plantillas de cada módulo van en `apps/<nombre_app>/templates/<nombre_app>/`. |
| `static/` | Archivos JavaScript e imágenes estáticas del sistema | Carpeta fuente conectada a Django mediante `STATICFILES_DIRS = [BASE_DIR / 'static']`. En producción, `collectstatic` compila en `staticfiles/`. |
| `media/` | Archivos multimedia subidos por los usuarios en tiempo de ejecución | Configurada con `MEDIA_ROOT = BASE_DIR / 'media'` y `MEDIA_URL = 'media/'`. Su contenido está completamente excluido de Git. |

## Nomenclatura y almacenamiento de archivos multimedia (`media/`)

> [!NOTE]
> **Estructura y convención preliminar:**
> La organización de carpetas y los patrones de nombres presentados a continuación representan **únicamente una propuesta de ejemplo**. La estructura definitiva para el almacenamiento de archivos multimedia aún no está confirmada ni cerrada para mantenerse de esta forma exacta, quedando sujeta a revisión y consenso del equipo según evolucionen los modelos de datos.

Para evitar subcarpetas innecesariamente anidadas y permitir identificar inmediatamente al propietario y contexto de cualquier archivo, se plantea como referencia una estructura por categoría con **nombres de archivo autodescriptivos**:

| Categoría | Convención del nombre de archivo | Ejemplo ilustrativo | Ventaja de identificación |
| :--- | :--- | :--- | :--- |
| **Avatar de usuario** | `avatars/user_{user_id}_avatar_{timestamp}.{ext}` | `media/avatars/user_42_avatar_20260915_143000.webp` | Identifica al usuario dueño directamente desde el archivo. |
| **Foto de mascota** | `pets/user_{owner_id}_pet_{pet_id}_{tipo}_{id_unico}.{ext}` | `media/pets/user_42_pet_7_avatar_20260915_143000.jpg` | Asocia la mascota con su dueño actual y el ID de la mascota. |
| **Multimedia de post** | `posts/user_{author_id}_post_{post_id}_{tipo}_{hash}.{ext}` | `media/posts/user_42_post_105_img_9f8e7d6c.png` | Atribuye el contenido al autor y post para auditoría y moderación. |

> [!IMPORTANT]
> **Nota sobre la estructura de carpetas e identificadores únicos:**
> Tanto la **organización de subcarpetas** (`avatars/`, `pets/`, `posts/`) como los nombres y la generación del identificador único (sea mediante marca de tiempo `timestamp`, UUIDv4, hash criptográfico o combinaciones de los mismos) son **únicamente propuestas y ejemplos ilustrativos de cómo podría estructurarse**. Ninguno de estos patrones está cerrado de forma definitiva; representan una guía de referencia para el principio de diseño (que los archivos sean fácilmente identificables y trazables) y la estructura final quedará sujeta a consenso del equipo según evolucionen los modelos de datos.

### Ventajas técnicas de la nomenclatura autodescriptiva
- **Autonomía del archivo:** Si el archivo se descarga, se comparte o se almacena en la nube (ejemplo: AWS S3), conserva su identidad y trazabilidad sin depender de su ruta.
- **Búsqueda inmediata:** Permite auditar y listar todos los recursos de un usuario en consola con comandos directos (ejemplo: `ls media/pets/user_42_*`).
- **Estructura limpia:** Mantiene las carpetas planas y organizadas por tipo de recurso en lugar de cientos de subdirectorios aislados.

## Flujo de trabajo en Git y GitHub Projects

Seguimos una metodología ágil donde cada tarea del tablero Kanban corresponde a un issue de GitHub (`#<issue-id>`).

### Ramas principales (protegidas)
- `main`: rama de producción. Contiene únicamente código estable, probado y listo para entrega.
- `develop`: rama de integración continua. Es el punto de partida y convergencia del trabajo activo del equipo.

> [!WARNING]
> Está terminantemente prohibido hacer push directo a las ramas `main` o `develop`. Todo cambio debe integrarse a través de un Pull Request revisado y aprobado.

### Ramas de trabajo
Las ramas de trabajo se derivan habitualmente de `develop` (salvo los `hotfix` que surgen de `main`). Para mantener total coherencia con los commits, el prefijo de la rama se alinea directamente con el tipo de tarea:

| Tipo de rama | Formato | Propósito | Ejemplo |
| :--- | :--- | :--- | :--- |
| Funcionalidad | `feat/<issue-id>-<slug>` | Nueva funcionalidad del producto | `feat/10-registro-usuario` |
| Corrección | `fix/<issue-id>-<slug>` | Solución de un error en integración (`develop`) | `fix/25-error-sesion` |
| Corrección urgente | `hotfix/<issue-id>-<slug>` | Parche crítico urgente directo a producción (`main`) | `hotfix/30-parche-seguridad` |
| Refactorización | `refactor/<issue-id>-<slug>` | Reestructuración de código sin alterar funcionalidad | `refactor/14-modularizar-servicios` |
| Pruebas | `test/<issue-id>-<slug>` | Adición o actualización de pruebas unitarias | `test/10-pruebas-auth` |
| Documentación | `docs/<issue-id>-<slug>` | Cambios exclusivos en manuales o documentación | `docs/8-actualizar-readme` |
| Estilo | `style/<issue-id>-<slug>` | Corrección de formato o indentación según PEP 8 | `style/8-ajustar-pep8` |
| Mantenimiento | `chore/<issue-id>-<slug>` | Ajuste de configuración, dependencias o tooling | `chore/10-ajustar-settings` |

### Pull Requests y cierre automático de tareas
1. Al concluir tu tarea, abre un Pull Request con destino a la rama `develop`.
2. En la descripción del Pull Request, utiliza la palabra clave de cierre:
   ```markdown
   Closes #<issue-id>
   ```
3. Solicita la revisión de al menos un compañero del equipo. Una vez aprobado y verificado, se realiza la fusión (merge).

> [!IMPORTANT]
> **Eliminación obligatoria de ramas:** una vez fusionado el Pull Request en `develop`, la rama de trabajo remota debe eliminarse en GitHub. En tu máquina local, actualiza `develop` y elimina la rama con `git branch -d nombre-de-la-rama` para evitar acumulación de ramas huérfanas.

### Formato de commits
Utilizamos Conventional Commits en minúsculas y en español, haciendo referencia al issue correspondiente:

```text
<tipo>(#<issue-id>): <descripción en imperativo>
```

| Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `feat` | Nueva funcionalidad o módulo | `feat(#10): implementar modelo de usuario y perfil humano` |
| `fix` | Corrección de un fallo o error | `fix(#25): corregir redirección en inicio de sesión` |
| `docs` | Cambios exclusivos en documentación | `docs(#8): actualizar flujo de trabajo en readme` |
| `style` | Formato e indentación según PEP 8 | `style(#8): ajustar formato de settings según pep8` |
| `refactor` | Reorganización de código sin alterar lógica | `refactor(#14): reorganizar capa de servicios de cuentas` |
| `test` | Incorporación o ajuste de pruebas | `test(#10): agregar pruebas unitarias de autenticación` |
| `chore` | Actualización de dependencias o configuración | `chore(#10): actualizar librerías en requirements` |

## Guía de estilo de código

Para mantener un código limpio, legible y uniforme entre todos los desarrolladores del equipo, se establecen las siguientes reglas obligatorias:

> [!IMPORTANT]
> **Regla de idiomas:**
> - **Código en inglés:** todos los identificadores (nombres de variables, funciones, clases, métodos, modelos, campos de base de datos, rutas de URLs y nombres de archivos) deben escribirse estrictamente en **inglés**.
> - **Comentarios en español:** todos los comentarios en el código, notas técnicas y cadenas de documentación (docstrings) deben redactarse exclusivamente en **español**.

### Convenciones de Python y PEP 8

| Elemento | Convención | Idioma | Ejemplo |
| :--- | :--- | :--- | :--- |
| Variables y funciones | `snake_case` | Inglés | `get_user_pets()`, `birth_date` |
| Clases y modelos | `PascalCase` | Inglés | `PetProfile`, `AdoptionRequest` |
| Constantes | `UPPER_SNAKE_CASE` | Inglés | `MAX_IMAGES_PER_POST`, `ADOPTION_STATUS` |
| Indentación | 4 espacios (soft tabs) | - | Configurado automáticamente vía `.editorconfig` con tecla Tab |
| Longitud de línea | 88 a 100 caracteres | - | Límite para legibilidad en revisiones |

### Organización de importaciones
Las importaciones en la cabecera de cada archivo deben agruparse en tres bloques separados por una línea en blanco:

```python
# 1. Librería estándar de Python
import os
from pathlib import Path

# 2. Django y librerías externas
from django.db import models

# 3. Módulos internos del proyecto
from apps.accounts.models import UserProfile
```

### Comentarios y documentación (docstrings)
- Redacta siempre los comentarios y docstrings en **español**, explicando el **porqué** de decisiones complejas y evitando comentar lo obvio.
- Emplea docstrings descriptivos al inicio de clases y funciones:
  ```python
  def transfer_pet_ownership(pet, new_owner):
      """
      Transfiere la titularidad de una mascota tras concretar una adopción.
      Actualiza el dueño asociado y desactiva la marca de en adopción.
      """
      pet.owner = new_owner
      pet.is_for_adoption = False
      pet.save()
  ```

### Buenas prácticas en Django
- **Modelos:**
  - Identificadores de clases y campos siempre en inglés (`class Pet(models.Model):`, `name = models.CharField(max_length=100)`).
  - Implementar siempre el método `__str__` para identificar las instancias en el panel de administración.
  - Definir la clase `Meta` con `verbose_name`, `verbose_name_plural` y ordenamiento predeterminado (`ordering`).
  - Utilizar campos de fecha automáticos (`auto_now_add=True` para creación, `auto_now=True` para actualización).
- **Vistas y URLs:**
  - Nombres de funciones, clases y rutas en inglés (ejemplo: `name='home'`, `name='pet-list'`).
  - **Espacios de nombres obligatorios (`app_name`):** cada archivo `urls.py` de aplicación debe declarar su identificador `app_name = '<nombre_app>'` para evitar colisiones entre módulos.
  - **Resolución inversa obligatoria:** queda terminantemente prohibido quemar rutas estáticas a mano en el código o en las plantillas (ejemplo: `href="/inicio/"` o `redirect('/inicio/')`). Todos los enlaces y redirecciones deben resolverse dinámicamente mediante:
    - En plantillas HTML: `{% url '<nombre_app>:<nombre_ruta>' %}`
    - En redirecciones Python (FBVs): `redirect('<nombre_app>:<nombre_ruta>')`
    - En código Python general / pruebas: `reverse('<nombre_app>:<nombre_ruta>')`
    - En atributos de clase (CBVs): `reverse_lazy('<nombre_app>:<nombre_ruta>')`
  - Mantener las vistas delgadas delegando la lógica de negocio a modelos o capas de servicio.
- **Plantillas HTML:**
  - `base.html` actúa como cascarón raíz mínimo e independiente de componentes de navegación.
  - **Regla de herencia de layouts:** cualquier plantilla dentro de `templates/layouts/` (como `app.html` o un futuro `auth.html`) debe heredar obligatoriamente de `base.html` mediante `{% extends 'base.html' %}`.
  - Enlaces de navegación resueltos siempre mediante la etiqueta `{% url %}`.

## Equipo de desarrollo

| Rol | Responsable |
| :--- | :--- |
| Product owners | María Paula Herrero & Sofía Marcano |
| UX/UI developer | Oriana Arellano |
| Database administrator | Bryan Silva |
| Frontend developer | Stefany Martínez |
| Backend developer | Edwyn Guzmán |
