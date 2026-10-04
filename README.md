# 🐾 Petly - Red social para mascotas

Plataforma colaborativa para amantes de los animales, desarrollada para la materia **Aplicaciones con Tecnología Internet (Semestre 2026-1)** de la Escuela de Computación de la Universidad Central de Venezuela.

## 📖 Sobre el proyecto

Petly conecta a dueños y amantes de los animales para compartir experiencias, buscar adopción responsable, encontrar pareja o socializar a sus mascotas de forma segura.

### ✨ Funcionalidades principales
-  **Perfiles dobles:** cada usuario maneja su perfil principal de humano y puede registrar múltiples perfiles para sus mascotas asociadas.
-  **Muro y multimedia:** publicaciones con fotos, videos, audios y enlaces, con soporte para menciones y comentarios anidados en hilo.
-  **Feeds especializados:**
   -  *Adopción responsable:* avisos de adopción, postulaciones y transferencia acordada de la mascota al nuevo dueño.
   -  *Búsqueda de pareja:* filtro y conexión entre mascotas compatibles.
   -  *Socialización:* aprendizaje y convivencia segura para animales domésticos.
-  **Comunicación y confianza:** mensajería directa por chat, sistema de reputación para encuentros presenciales y moderación de contenido.

## 🛠️ Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| Lenguaje | Python 3.12+ | Lenguaje base del proyecto |
| Framework web | Django 6.1+ | Backend, ORM y arquitectura web |
| Estilos CSS | Tailwind CSS v4 | Sistema de diseño y utilidades visuales |
| Base de datos | SQLite | Persistencia relacional de datos en volumen Docker |
| Contenedores | Docker y Docker Compose | Estandarización y aislamiento del entorno de desarrollo |
| Recarga en vivo | django-browser-reload | Refresco automático del navegador ante cambios en plantillas y estilos |
| Calidad de código | Ruff | Linter y formateador ultrarrápido según PEP 8 |
| Integración continua | GitHub Actions | Automatización de pruebas, verificación de migraciones y estilos |
| Control de versiones | Git y GitHub | Repositorio y control de versiones |
| Gestión del proyecto | GitHub Projects | Tablero Kanban y trazabilidad de issues |

## 🚀 Puesta en marcha

### 🐳 Opción recomendada: Docker y Docker Compose

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

# 3. Aplicar las migraciones (obligatorio la primera vez que se inicia el proyecto)
docker compose exec web python manage.py migrate
```

La aplicación estará lista y accesible en [http://localhost:8000/](http://localhost:8000/).

> [!NOTE]
> **Migraciones iniciales y persistencia en el volumen de Docker:**
> - La ejecución del comando de migraciones (`python manage.py migrate`) es **estrictamente obligatoria la primera vez** que levantas el proyecto para inicializar el archivo `db.sqlite3` con todas las tablas del sistema dentro del volumen.
> - La base de datos SQLite vive y se resguarda dentro del **volumen administrado por Docker (`petly_db_data`)**, el cual opera de forma totalmente aislada de tu sistema de archivos local.
> - Aunque elimines archivos en tu máquina anfitriona o no exista una carpeta local `data/`, **la base de datos dentro del volumen NO se borra ni se ve afectada**.
> - La base de datos únicamente se reiniciará o borrará si ejecutas explícitamente `docker compose down -v` (con la bandera `-v` de volúmenes). Con el comando habitual `docker compose down`, todos tus datos se conservan íntegros para el siguiente inicio.


---

### ⚡ Recarga automática en el navegador (Live Reload)

El entorno de desarrollo incluye recarga automática en vivo mediante **`django-browser-reload`** y el compilador continuo de **Tailwind CSS v4**:
- Al modificar y guardar cualquier archivo de plantilla HTML (`.html`), hoja de estilos (`.css`) o vista de Python (`.py`), **la pestaña de tu navegador se recarga sola de forma inmediata**, sin necesidad de presionar `F5`.
- Tailwind CSS se ejecuta en segundo plano dentro del contenedor `petly_web` y recompila las nuevas clases en ~150 ms.
- Esta funcionalidad está condicionada exclusivamente a `DEBUG=True` en [config/settings.py](config/settings.py) y [config/urls.py](config/urls.py), por lo que se desactiva por completo en producción sin generar sobrecarga.

---

### 📦 Gestión e instalación de dependencias en Docker

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

### 💻 Comandos frecuentes de Docker

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

### 🐍 Opción alternativa: Entorno virtual local (.venv)

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

### 🔐 Variables de entorno (`.env.dev`)

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

## 📁 Estructura del proyecto

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
├── .github/                      # Flujos automatizados de GitHub Actions
│   └── workflows/
│       └── ci.yml                # Pipeline de Integración Continua (CI)
├── .gitignore                    # Reglas de exclusión de Git
├── Dockerfile                    # Definición de la imagen del contenedor web
├── docker-compose.yml            # Orquestación de servicios (web y base de datos)
├── manage.py                     # Utilidad de línea de comandos de Django
├── pyproject.toml                # Configuración de reglas y exclusiones de Ruff
└── requirements.txt              # Dependencias de Python del proyecto
```

> [!NOTE]
> La carpeta `apps/<module_name>/` en este diagrama funciona como **plantilla de referencia arquitectónica** para la creación de futuros módulos. Actualmente, el proyecto cuenta con la aplicación inicial **`apps.core`**, la cual actúa como núcleo del sistema proveyendo modelos base abstractos (`TimeStampedModel` para auditoría temporal), utilidades transversales y la vista de inicio del portal público.

### 🏛️ Principios de la arquitectura modular

| Carpeta | Propósito | Reglas de configuración |
| :--- | :--- | :--- |
| `apps/` | Aloja los dominios del sistema separados en submódulos independientes | Cada app configura su clase en `apps.py` con `name = 'apps.<nombre_app>'` y su enrutador `urls.py` con `app_name = '<nombre_app>'` para la resolución inversa con `{% url %}`. |
| `theme/` | Gestión y compilación del sistema de diseño Tailwind CSS | Contiene la configuración de estilos fuente y genera el paquete CSS unificado en `theme/static/css/dist/styles.css`. |
| `templates/` | Plantilla base global, layouts intermedios y componentes reutilizables | `base.html` es el cascarón raíz. Todo layout dentro de `templates/layouts/` (ej. `app.html`) debe heredar obligatoriamente de `base.html` con `{% extends 'base.html' %}`. Las plantillas de cada módulo van en `apps/<nombre_app>/templates/<nombre_app>/`. |
| `static/` | Archivos JavaScript e imágenes estáticas del sistema | Carpeta fuente conectada a Django mediante `STATICFILES_DIRS = [BASE_DIR / 'static']`. En producción, `collectstatic` compila en `staticfiles/`. |
| `media/` | Archivos multimedia subidos por los usuarios en tiempo de ejecución | Configurada con `MEDIA_ROOT = BASE_DIR / 'media'` y `MEDIA_URL = 'media/'`. Su contenido está completamente excluido de Git. |

## 🖼️ Nomenclatura y almacenamiento de archivos multimedia (`media/`)

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

### 💡 Ventajas técnicas de la nomenclatura autodescriptiva
- **Autonomía del archivo:** Si el archivo se descarga, se comparte o se almacena en la nube (ejemplo: AWS S3), conserva su identidad y trazabilidad sin depender de su ruta.
- **Búsqueda inmediata:** Permite auditar y listar todos los recursos de un usuario en consola con comandos directos (ejemplo: `ls media/pets/user_42_*`).
- **Estructura limpia:** Mantiene las carpetas planas y organizadas por tipo de recurso en lugar de cientos de subdirectorios aislados.

## 🔄 Flujo de trabajo en Git y GitHub Projects

Seguimos una metodología ágil donde cada tarea del tablero Kanban corresponde a un issue de GitHub (`#<issue-id>`).

### 🛡️ Ramas principales
- `main`: rama de producción protegida. Contiene únicamente código estable, probado y listo para entrega oficial.
- `develop`: rama de integración continua protegida. Es el punto de partida y convergencia del trabajo activo del equipo.

> [!WARNING]
> **Protección estricta de `main`:** está terminantemente prohibido hacer push directo a la rama `main`. Todo paso a producción debe integrarse exclusivamente a través de un Pull Request con revisión, aprobación obligatoria de al menos un compañero y con la suite de CI en verde bloqueante.
>
> **Reglas de protección en `develop`:** para mantener un equilibrio entre agilidad y calidad de código, `develop` cuenta con reglas de protección configuradas:
> - **Fusión exclusiva mediante Pull Request:** no se permite push directo a `develop`; cada tarea debe desarrollarse en su propia rama aislada (`feat/...`, `fix/...`, etc.) siguiendo la convención del proyecto.
> - **Sin aprobación requerida:** no es obligatorio el visto bueno o aprobación de otro compañero para fusionar, permitiendo que el propio desarrollador integre su PR de manera autónoma.
> - **CI obligatorio y bloqueante:** el pipeline de CI debe finalizar completamente en **verde (✅)**. Si alguna prueba o verificación falla, GitHub bloqueará la fusión y el desarrollador deberá corregir el código en su rama y subir nuevos commits hasta que todas las comprobaciones pasen exitosamente.

### 🌿 Ramas de trabajo
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

### 🔀 Pull Requests y cierre automático de tareas
1. Al concluir tu tarea, abre un Pull Request con destino a la rama `develop`.
2. En la descripción del Pull Request, utiliza la palabra clave de cierre vinculada al issue:
   ```markdown
   Closes #<issue-id>
   ```
   *Esto cerrará el issue automáticamente al fusionar el PR y moverá la tarjeta asociada a **Done** en el tablero Kanban del proyecto.*
3. El pipeline de CI se ejecutará automáticamente. Al estar configurado como bloqueante en `develop`, GitHub no habilitará el botón de **Merge pull request** hasta que los 5 controles finalicen en **verde (✅)**. Si algún control falla, el desarrollador deberá corregir el código en su rama local y subir los cambios (`push`) hasta que todas las pruebas pasen. Al no requerir aprobación de terceros, una vez el CI esté en verde, el autor podrá realizar el merge directamente.
4. Al hacer **Merge**:
   - **Ramas de trabajo temporales:** GitHub **elimina la rama remota de la tarea automáticamente** al fusionarse en `develop` gracias a la política (*Automatically delete head branches*).
   - **Inmunidad de `develop` y `main`:** las ramas base cuentan con protección contra borrado accidental; al realizar el pase de `develop` hacia `main`, la rama `develop` permanece intacta y nunca se elimina.
   - En tu máquina local, actualiza `develop` y elimina la rama local que ya fue integrada:
     ```bash
     git checkout develop
     git pull origin develop
     git branch -d nombre-de-la-rama
     git fetch -p   # Limpia las referencias locales a ramas remotas ya eliminadas
     ```

### 🤖 Integración continua (CI) con GitHub Actions

El repositorio cuenta con un pipeline automatizado en [.github/workflows/ci.yml](.github/workflows/ci.yml) que se dispara automáticamente ante cada `pull_request` hacia las ramas `develop` y `main`.

El pipeline ejecuta de manera nativa los siguientes 5 controles de calidad:

1. **Calidad de código y estilo (Ruff):**
   - Ejecuta `ruff check .` para detectar variables sin usar, imports innecesarios y malas prácticas.
   - Ejecuta `ruff format --check .` para verificar que todo el código cumpla con el formato estricto de PEP 8.
   - *Comandos locales para auto-formatear antes de hacer commit:*
     ```bash
     ruff format .      # Formatea automáticamente todo el proyecto
     ruff check --fix . # Corrige automáticamente errores de código e imports
     ```
2. **Chequeo de configuración de Django:**
   - Ejecuta `python manage.py check --fail-level WARNING` para garantizar que la configuración del proyecto y de las aplicaciones sea válida.
3. **Verificación de migraciones pendientes:**
   - Ejecuta `python manage.py makemigrations --check --dry-run` para impedir que se suban modificaciones a los modelos sin su respectivo archivo de migración.
4. **Compilación de estilos de Tailwind CSS v4:**
   - Ejecuta `tailwindcss -i theme/static_src/src/styles.css -o theme/static/css/dist/styles.css --minify` para validar que las hojas de estilos compilen limpiamente.
5. **Suite de pruebas unitarias:**
   - Ejecuta `python manage.py test` para verificar que todas las pruebas pasen exitosamente.

> [!WARNING]
> Ningún Pull Request debe fusionarse si el flujo de Integración Continua no finaliza en **verde (✅)**.

### 📝 Formato de commits
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

## 📐 Guía de estilo de código

Para mantener un código limpio, legible y uniforme entre todos los desarrolladores del equipo, se establecen las siguientes reglas obligatorias:

> [!IMPORTANT]
> **Regla de idiomas:**
> - **Código en inglés:** todos los identificadores (nombres de variables, funciones, clases, métodos, modelos, campos de base de datos, rutas de URLs y nombres de archivos) deben escribirse estrictamente en **inglés**.
> - **Comentarios en español:** todos los comentarios en el código, notas técnicas y cadenas de documentación (docstrings) deben redactarse exclusivamente en **español**.

### 🐍 Convenciones de Python y PEP 8

| Elemento | Convención | Idioma | Ejemplo |
| :--- | :--- | :--- | :--- |
| Variables y funciones | `snake_case` | Inglés | `get_user_pets()`, `birth_date` |
| Clases y modelos | `PascalCase` | Inglés | `PetProfile`, `AdoptionRequest` |
| Constantes | `UPPER_SNAKE_CASE` | Inglés | `MAX_IMAGES_PER_POST`, `ADOPTION_STATUS` |
| Indentación | 4 espacios (soft tabs) | - | Configurado automáticamente vía `.editorconfig` con tecla Tab |
| Longitud de línea | 88 a 100 caracteres | - | Límite para legibilidad en revisiones |

### 📦 Organización de importaciones
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

### 💬 Comentarios y documentación (docstrings)
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

## 🎯 Buenas prácticas en Django y arquitectura

### 🗄️ Modelos, persistencia y capa de servicios
- **Separación de responsabilidades (Fat Models/Services, Thin Views):** Mantener las vistas con lógica mínima delegando reglas de negocio complejas a la capa de servicios (`apps/<modulo>/services.py`) o a métodos propios del modelo.
- **Nomenclatura en inglés:** Nombres de clases en `PascalCase` y atributos en `snake_case`, siempre en inglés (`class Pet(models.Model):`, `name = models.CharField(max_length=100)`).
- **Identificación amigable (`__str__`):** Implementar obligatoriamente el método `__str__` en cada modelo para facilitar la administración y depuración.
- **Metadatos obligatorios (`class Meta`):** Definir siempre `verbose_name`, `verbose_name_plural` y el ordenamiento predeterminado (`ordering`).
- **Auditoría temporal estándar:** Utilizar campos de fecha automáticos (`created_at` con `auto_now_add=True` para creación y `updated_at` con `auto_now=True` para modificación).

### 🌐 Contrato de enrutamiento y URLs (Zero-Collision)
Para garantizar el desarrollo concurrente sin bloqueos entre frontend y backend, se establece un contrato estricto de enrutamiento:

- **Espacios de nombres obligatorios (`app_name`):** Cada archivo `urls.py` dentro de `apps/<modulo>/` debe declarar su variable `app_name = '<modulo>'` para evitar colisiones de rutas entre aplicaciones.
- **Nombres de ruta semánticos en inglés:** Todo identificador de ruta (`name`) debe escribirse en inglés y en formato `snake_case`, siguiendo el patrón semántico `<entidad>_<acción>` (ej. `pet_list`, `pet_create`).
- **Resolución inversa obligatoria (Cero rutas quemadas):** Queda terminantemente prohibido escribir rutas estáticas a mano en plantillas o vistas (ejemplo: `href="/inicio/"`, `href="#"` o `redirect('/pets/')`). Todos los enlaces y redirecciones deben resolverse dinámicamente mediante:
  - En plantillas HTML: `{% url '<nombre_app>:<nombre_ruta>' %}`
  - En vistas por funciones (FBVs): `redirect('<nombre_app>:<nombre_ruta>')`
  - En vistas por clases (CBVs): `reverse_lazy('<nombre_app>:<nombre_ruta>')`
  - En servicios o pruebas: `reverse('<nombre_app>:<nombre_ruta>')`

> [!IMPORTANT]
> **Desarrollo concurrente sin bloqueos:**
> Siguiendo este catálogo, el desarrollador Frontend/UX puede vincular enlaces y botones en las plantillas (ej. `href="{% url 'accounts:profile' %}"` o `href="{% url 'pets:pet_create' %}"`) antes de que el Backend implemente las vistas correspondientes, garantizando cero colisiones y evitando errores de `NoReverseMatch`.

#### 📋 Catálogo estándar de operaciones y nombres de ruta

| Operación | Patrón de `name` | URL Relativa sugerida | Propósito / Pantalla |
| :--- | :--- | :--- | :--- |
| **Listado / Principal** | `<entidad>_list` | `/<modulo>/` | Pantalla de índice o listado general |
| **Creación** | `<entidad>_create` | `/<modulo>/create/` | Formulario de registro o alta de recurso |
| **Detalle** | `<entidad>_detail` | `/<modulo>/<int:pk>/` | Ficha informativa de un registro específico |
| **Edición** | `<entidad>_edit` | `/<modulo>/<int:pk>/edit/` | Formulario de actualización o modificación |
| **Eliminación** | `<entidad>_delete` | `/<modulo>/<int:pk>/delete/` | Confirmación o endpoint de borrado |
| **Acción de flujo** | `<entidad>_<accion>` | `/<modulo>/<accion>/` | Flujos específicos (ej. `match_feed`, `login`) |

#### 💡 Ejemplo práctico de uso

1. **Definición en el enrutador del módulo (`apps/pets/urls.py`):**
```python
from django.urls import path

from apps.pets import views

app_name = 'pets'

urlpatterns = [
    # Colección y creación
    path('', views.PetListView.as_view(), name='pet_list'),
    path('create/', views.PetCreateView.as_view(), name='pet_create'),
    # Operaciones sobre una entidad concreta (con identificador)
    path('<int:pk>/', views.PetDetailView.as_view(), name='pet_detail'),
    path('<int:pk>/edit/', views.PetUpdateView.as_view(), name='pet_edit'),
    path('<int:pk>/delete/', views.PetDeleteView.as_view(), name='pet_delete'),
    # Flujos de negocio específicos
    path('match/feed/', views.MatchFeedView.as_view(), name='match_feed'),
]
```

2. **Consumo en plantillas HTML (`templates/`):**
```html
{# Enlaces globales sin parámetros (navbar o botones principales) #}
<a href="{% url 'pets:pet_list' %}" class="...">Mis Mascotas</a>
<a href="{% url 'pets:pet_create' %}" class="...">Registrar Mascota</a>

{# Enlaces dinámicos con parámetros (dentro de tarjetas, bucles o tablas) #}
{% for pet in pets %}
    <a href="{% url 'pets:pet_detail' pet.pk %}" class="...">Ver Detalle</a>
    <a href="{% url 'pets:pet_edit' pet.pk %}" class="...">Editar</a>
{% endfor %}

{# Enlaces entre módulos distintos #}
<a href="{% url 'accounts:login' %}" class="...">Iniciar Sesión</a>
<a href="{% url 'pets:match_feed' %}" class="...">Buscar Pareja</a>
```

3. **Consumo en Python (Vistas, Redirecciones y Pruebas):**
```python
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy


# En Vistas Basadas en Funciones (FBVs)
def pet_create_view(request):
    # Lógica de guardado...
    return redirect('pets:pet_list')


# En Vistas Basadas en Clases (CBVs)
class PetDeleteView(DeleteView):
    model = Pet
    success_url = reverse_lazy('pets:pet_list')


# En servicios o pruebas unitarias (con argumentos)
def test_pet_detail_redirect():
    url = reverse('pets:pet_detail', kwargs={'pk': pet.pk})
```


## 🎨 Sistema de diseño y componentes UI

### 🏗️ Arquitectura de plantillas y layouts

El sistema visual de Petly está diseñado siguiendo el principio de herencia en cascada limpia:

- **Cascarón raíz (`templates/base.html`):** Contiene la estructura HTML5 esencial (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`), etiquetas meta para responsividad, enlaces a hojas de estilos compiladas y el bloque `{% block base_content %}`. Es completamente agnóstico de componentes de navegación.
- **Tipografías autohospedadas (100% offline):** Las fuentes oficiales **Plus Jakarta Sans** (titulares, botones y llamadas a la acción) e **Inter** (cuerpo de texto y respaldo) están alojadas localmente en formato binario optimizado `.woff2` en `static/fonts/`. Esto elimina cualquier dependencia de CDNs externos como Google Fonts, garantizando funcionamiento sin conexión a internet y máxima privacidad.
- **Layouts base (`templates/layouts/`):**
  - **`app.html`:** Layout principal autenticado. Incorpora la barra de navegación superior (`navbar.html`), contenedor central delimitado (`max-w-7xl`), sistema de notificaciones flash (`messages.html`) y pie de página (`footer.html`).
  - **`public.html`:** Layout para flujos públicos (bienvenida, inicio de sesión, registro y recuperación de contraseña). Utiliza una cabecera simplificada (`navbar_public.html`) y un diseño despejado.

#### 🔤 Escala tipográfica oficial

Definida en `theme/static_src/src/styles.css` con clases semánticas reutilizables:

| Clase de utilidad | Tamaño | Peso / Kerning | Uso oficial |
| :--- | :--- | :--- | :--- |
| `.title-h1` | 48px / 1.15 | 700 Bold / -0.015em | Título principal de pantallas hero y bienvenida |
| `.title-h2` | 36px / 1.20 | 700 Bold / -0.015em | Encabezados de páginas de gestión y secciones |
| `.title-h3` | 28px / 1.25 | 600 SemiBold / -0.015em | Títulos de tarjetas de perfil y modales |
| `.title-h4` | 22px / 1.30 | 600 SemiBold / -0.015em | Subtítulos de bloques y agrupadores de formulario |
| `.title-h5` | 18px / 1.35 | 500 Medium / normal | Títulos secundarios y cabeceras de diálogo |
| `.title-h6` | 14px / 1.40 | 500 Medium / normal | Encabezados de métricas y pestañas |
| `.text-display` | 24px / 1.40 | Regular a Bold | Textos destacados y lemas promocionales |
| `.text-large` | 18px / 1.45 | Regular a Bold | Descripciones de cabecera y resúmenes |
| `.text-body-base` | 14px / 1.50 | Regular (400) | Párrafos generales, etiquetas y textos estándar |
| `.text-caption` | 12px / 1.50 | Regular a Medium | Notas al pie, marcas de tiempo y textos de ayuda |

### 🖌️ Tokens de diseño y colores corporativos

Configurados en Tailwind CSS v4 (`theme/static_src/src/styles.css`) en concordancia con el prototipo oficial (`docs/reto_11_ diseño_prototipo.pdf`):

| Token | Hexadecimal | Propósito y aplicación en interfaz |
| :--- | :--- | :--- |
| `petly-coral` / `brand-500` | `#FA7D82` | Color primario de marca, botones principales, anillos de foco y acentos activos |
| `petly-coral-dark` / `brand-700` | `#A53B42` | Estados `:hover`/`:active` de botones primarios y enlaces destacados |
| `petly-coral-light` / `brand-100` | `#FFDAD9` | Contenedores suaves, botón terciario y chip de género hembra |
| `petly-surface` | `#F9F9FF` | Fondo base de la aplicación y lienzo de pantallas |
| `petly-blue` | `#DEE8FF` | Botones secundarios, contenedor de filtros y chip de género macho |
| `petly-ice` | `#E7EEFF` | Fondo celeste hielo de entradas de formulario (`.input-petly`) |
| `petly-mint` | `#8FFFB4` | Insignias de compatibilidad (98%), pedigrí certificado y confirmaciones |
| `petly-lilac` | `#F5D0FF` | Chips de rasgos de personalidad y personalidad de mascotas |
| `petly-purple` | `#74567E` | Texto sobre contenedores lila y acentos complementarios |
| `neutral-800` | `#2B2B2B` | Color de texto principal para títulos y elementos interactivos |
| `neutral-700` | `#4A4A4A` | Subtítulos, etiquetas de campos y textos descriptivos |
| `neutral-500` | `#757575` | Texto atenuado, pie de página, iconos neutros y leyendas |
| `neutral-300` | `#E0E0E0` | Bordes de tarjetas, separadores y contornos inactivos |

### 🧩 Catálogo de componentes modulares (`templates/components/`)

Todos los componentes son reutilizables y aceptan parámetros vía la etiqueta `{% include %}` de Django:

#### 1. Navegación y estructura institucional
* **`navbar.html`:** Barra de navegación autenticada completa con logotipo distintivo (`🐾`), enlaces centrales con pastilla de estado activo, buscador, selector de idioma interactivo y menú de usuario.
* **`navbar_public.html`:** Cabecera ligera para páginas de bienvenida, login y registro, manteniendo consistencia de marca y selector de idioma.
* **`footer.html`:** Pie de página institucional bilingüe con lema corporativo, enlaces normativos y derechos reservados.

#### 2. Botones y controles de acción (`button.html`)
Renderiza elementos `<button>` o enlaces `<a>` (cuando se pasa el parámetro `href`), soportando variantes visuales y botones flotantes (FAB):
```django
{# Botón primario coral con ícono #}
{% include 'components/button.html' with text="Guardar cambios" variant="primary" icon="paw" %}

{# Botones de acción flotantes (FAB) para búsqueda de pareja #}
{% include 'components/button.html' with variant="fab-dismiss" %}
{% include 'components/button.html' with variant="fab-add" %}
{% include 'components/button.html' with variant="fab-like" %}
```
* **Variantes de botón:** `primary` (coral), `secondary` (azul suave), `soft` (rosa terciario), `lilac` (púrpura suave), `outline` (borde sutil), `danger` (rojo descarte).
* **Variantes FAB:** `fab-dismiss` (descartar ✕), `fab-add` (añadir +), `fab-like` (me interesa ♥).

#### 3. Insignias y etiquetas (`badge.html`)
Pastillas cromáticas para resaltar afinidad porcentual, temperamentos o género:
```django
{% include 'components/badge.html' with text="98% compatibilidad" variant="compat" %}
{% include 'components/badge.html' with text="Juguetón" variant="tag" %}
{% include 'components/badge.html' with text="Macho" variant="male" %}
{% include 'components/badge.html' with text="Hembra" variant="female" %}
```

#### 4. Entradas de formulario (`input.html`)
Campos redondeados con fondo celeste hielo (`.input-petly`), anillo de foco coral e integración de íconos frontales y posteriores:
```django
{% include 'components/input.html' with name="username" label="Usuario" placeholder="Escribe tu usuario" icon="user" %}
{% include 'components/input.html' with name="password" label="Contraseña" type="password" icon="lock" icon_end="eye" %}
```

#### 5. Interruptores de alternancia (`toggle.html`)
Switch booleano accesible con 2px de margen simétrico y transición suave entre coral (activo) y azul hielo (inactivo):
```django
{% include 'components/toggle.html' with id="match-toggle" name="is_matching" label="Buscando pareja" checked=True %}
```

#### 6. Control segmentado (`segmented.html`)
Selector de pastillas para alternar entre opciones excluyentes (modo de vista, especie o género):
```django
{% include 'components/segmented.html' with text_1="Perros" text_2="Gatos" active_index=1 %}
```

#### 7. Tarjetas y contenedores (`card.html`)
Contenedor base `.card-petly` con bordes redondeados (`rounded-3xl`), sombra sutil y fondo blanco inmaculado.

#### 8. Modales de confirmación (`confirmation_modal.html`)
Ventana emergente interactiva autocontenida para confirmar acciones importantes o destructivas:
```django
{% include 'components/confirmation_modal.html' with id="modal-delete" variant="danger" icon="trash" title="¿Eliminar mascota?" text="Esta acción no se puede deshacer." confirm_text="Eliminar" cancel_text="Cancelar" %}
```
* **Control mediante JavaScript:** Funciones globales `openModal('modal-id')` y `closeModal('modal-id')`, con soporte de cierre por tecla `Escape` o clic en el fondo semitransparente.

#### 9. Mensajes y alertas del sistema (`messages.html`)
Banners de notificación integrados con el framework `django.contrib.messages` (éxito, error, advertencia e información) con botón de cierre accesible.

---

### 🐾 Sistema y biblioteca de íconos vectoriales (`icon.html`)

El componente `templates/components/icon.html` gestiona el catálogo de íconos SVG de la aplicación:

```django
{# Uso estándar (máscara CSS con herencia de color) #}
{% include 'components/icon.html' with name="paw" class="w-5 h-5 text-petly-coral" %}

{# Renderizado como etiqueta <img> directa #}
{% include 'components/icon.html' with name="palette" class="w-6 h-6" as_img=True %}
```

#### ⚙️ Mecanismo de renderizado
* **Máscara CSS dinámica:** Por defecto, renderiza un `<span>` con `mask-image: url('images/icons/<name>.svg')` y la clase `bg-current`. Esto permite que el ícono adopte **automáticamente cualquier color de texto de Tailwind** (`text-petly-coral`, `text-white`, `text-neutral-500`, etc.) sin necesidad de manipular el archivo SVG.
* **Geometría estandarizada:** Todos los íconos están normalizados en una cuadrícula `viewBox="0 0 24 24"`, trazo uniforme de `2px` con remates redondeados (`stroke-linecap="round"`).
* **Transparencia calada:** Los íconos con relleno (como `checkbox-checked`, `smile`, `user-circle`) utilizan calados vectoriales nativos (`alpha=0`) para garantizar su compatibilidad tanto en modo máscara como en modo imagen directa.

#### 📚 Catálogo completo de íconos disponibles (`static/images/icons/`)

| Categoría | Íconos disponibles (`name`) |
| :--- | :--- |
| **Navegación e interfaz** | `caret-up`, `caret-down`, `chevron-up`, `chevron-down`, `close`, `eye`, `location`, `lock`, `globe` |
| **Acciones y controles** | `plus`, `plus-circle`, `minus`, `sliders`, `trash`, `camera`, `camera-plus`, `palette` |
| **Mascotas y especie** | `paw`, `paw-double`, `dog`, `award` (pedigrí/certificado), `cake` (edad/cumpleaños), `female`, `male` |
| **Afinidad y adopción** | `heart`, `heart-filled`, `hand-heart` (outline), `hand-heart-filled` (sólido) |
| **Usuarios y social** | `user`, `user-circle`, `users`, `id-card`, `mail`, `phone`, `message-square`, `message-square-text`, `smile` |
| **Formularios y estados** | `checkbox`, `checkbox-checked`, `check`, `check-circle`, `dot`, `file-up`, `star`, `sparkle`, `sparkles` |

---

### 🖼️ Catálogo interactivo de componentes en vivo (`components_palette.html`)

Para facilitar la maquetación y validación del equipo, la pantalla de inicio (`templates/components/components_palette.html`) integra una galería interactiva con todos los componentes del sistema:

* Botones en todas sus variantes y estados `:hover`/`:active`.
* Botones flotantes (FAB) con sus colores y sombras oficiales.
* Insignias cromáticas y etiquetas semánticas.
* Entradas de formulario e interruptores de alternancia funcionales.
* Diálogos modales interactivos en vivo (`demo-modal-danger` y `demo-modal-match`).
* Soporte bilingüe en tiempo real con conmutación dinámica `ES` / `EN`.


## 🌍 Internacionalización y localización (i18n / l10n)

El proyecto cuenta con soporte bilingüe predeterminado (**español `es`** como idioma principal e **inglés `en`** como secundario), cumpliendo con los estándares de accesibilidad y las heurísticas de Nielsen (ayuda y documentación, coincidencia con el mundo real).

### ⚙️ Arquitectura del sistema
- **Middleware:** `LocaleMiddleware` está ubicado estrictamente entre `SessionMiddleware` y `CommonMiddleware` en `config/settings.py` para resolver las preferencias de idioma en cada petición.
- **Context Processor:** `django.template.context_processors.i18n` expone las variables globales (`LANGUAGES`, `LANGUAGE_CODE`) a las plantillas.
- **Selector accesible:** La barra de navegación incluye un conmutador con formulario `POST` hacia la vista `set_language`, que actualiza la cookie `django_language` y recarga la vista conservando el contexto.
- **Catálogos:** Las traducciones residen en `locale/<idioma>/LC_MESSAGES/`.

### 📝 Marcado de cadenas para traducción

#### 1. En plantillas HTML (`.html`)
Carga la biblioteca `{% load i18n %}` al inicio del archivo:

```html
{% load i18n %}

{# Textos simples #}
<h1>{% translate "Gestión de perfiles de mascotas" %}</h1>
<button>{% translate "Guardar cambios" %}</button>

{# Textos dinámicos con variables contextuales #}
{% blocktranslate with name=pet.name %}
    La mascota {{ name }} ha sido actualizada con éxito.
{% endblocktranslate %}
```

#### 2. En código Python (`.py`)
Utiliza la función correspondiente según el momento en que se evalúa la cadena:

* **En Modelos y Formularios — `gettext_lazy as _`:**
  - **Uso:** En `verbose_name`, `help_text`, etiquetas de formularios (`label`) y mensajes de validación (`error_messages`).
  - **Motivo:** Los modelos y formularios se cargan en memoria al iniciar el servidor (cuando aún no existe una petición HTTP activa). `gettext_lazy` retrasa la traducción hasta el momento en que el texto se renderiza ante el usuario.
  ```python
  from django.db import models
  from django.utils.translation import gettext_lazy as _


  class Pet(models.Model):
      name = models.CharField(
          max_length=100,
          verbose_name=_('Nombre de la mascota'),
          help_text=_('Indica el nombre oficial o apodo de la mascota.'),
      )

      class Meta:
          verbose_name = _('Mascota')
          verbose_name_plural = _('Mascotas')
  ```

* **En Vistas y Notificaciones — `gettext as _`:**
  - **Uso:** En mensajes flash (`messages.success`, `messages.error`), títulos dinámicos en el contexto y respuestas en tiempo de ejecución.
  - **Motivo:** Dentro de la vista ya existe una petición activa (`request`), por lo que el idioma del usuario ya está resuelto y la traducción se efectúa de inmediato.
  ```python
  from django.contrib import messages
  from django.shortcuts import redirect
  from django.utils.translation import gettext as _


  def profile_update_view(request):
      messages.success(request, _('Tu perfil fue actualizado con éxito.'))
      return redirect('accounts:profile')
  ```

### 📖 Gestión de archivos de traducción (`.po` y `.mo`)
El archivo `.po` (*Portable Object*) asocia cada mensaje original con su traducción:

```po
msgid "Gestión de perfiles de mascotas"
msgstr "Pet profile management"
```

- **`msgid` (identificador):** Frase original extraída del código. No debe editarse manualmente.
- **`msgstr` (traducción):** Texto traducido en el idioma destino. Si se deja vacío (`""`), Django muestra el texto en español por defecto.

> [!IMPORTANT]
> **Eliminar la marca `#, fuzzy`:**
> Al modificar frases en el código, Django puede marcar traducciones previas con `#, fuzzy` (*traducción tentativa*). **Django ignora cualquier traducción con esta marca**. Una vez revisada y confirmada la traducción, **elimina la línea `#, fuzzy`** para que se active en la interfaz.

### 🐳 Flujo de trabajo paso a paso con Docker

Para gestionar traducciones en el entorno contenerizado de Docker Compose:

1. **Marcar textos:** Añadir `{% translate "..." %}` en plantillas o `_("...")` en código Python.
2. **Extraer cadenas:** Escanear el código para actualizar los archivos `.po`:
   ```bash
   docker compose exec web python manage.py makemessages -a -i '.venv/*' -i 'node_modules/*'
   ```
3. **Traducir:** Abrir `locale/en/LC_MESSAGES/django.po`, completar los `msgstr ""` pendientes y retirar las etiquetas `#, fuzzy`.
4. **Compilar binarios:** Generar los archivos binarios optimizados `.mo`:
   ```bash
   docker compose exec web python manage.py compilemessages
   ```
5. **Verificar en el navegador:** Acceder a [http://localhost:8000/](http://localhost:8000/) y utilizar el selector de idioma para comprobar la conmutación entre `ES` y `EN`.



## 👥 Equipo de desarrollo
Este proyecto es diseñado y construido por:
* **Product Owners**: María Paula Herrero & Sofía Marcano.
* **UX/UI Developer**: Oriana Arellano.
* **Database Administrator**: Bryan Silva.
* **Frontend Developer**: Stefany Martínez.
* **Backend Developer**: Edwyn Guzmán.
