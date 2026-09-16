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

## Equipo de desarrollo

| Rol | Responsable |
| :--- | :--- |
| Product owners | María Paula Herrero & Sofía Marcano |
| UX/UI developer | Oriana Arellano |
| Database administrator | Bryan Silva |
| Frontend developer | Stefany Martínez |
| Backend developer | Edwyn Guzmán |

## Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| Lenguaje | Python 3.14+ | Lenguaje base del proyecto |
| Framework web | Django 6.1+ | Backend, ORM y arquitectura web |
| Base de datos | SQLite | Persistencia relacional de datos |
| Control de versiones | Git y GitHub | Repositorio y control de versiones |
| Gestión del proyecto | GitHub Projects | Tablero Kanban y trazabilidad de issues |

## Puesta en marcha

Sigue estos pasos para configurar y ejecutar el proyecto en tu entorno local:

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone <url-del-repositorio>
cd pet-social-network

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Actualizar pip e instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4. Aplicar las migraciones de base de datos (crea data/db.sqlite3)
python manage.py migrate

# 5. Iniciar el servidor de desarrollo
python manage.py runserver
```

La aplicación estará accesible en `http://127.0.0.1:8000/`.

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
├── data/                         # Almacenamiento local de base de datos SQLite (ignorado en Git)
├── media/                        # Archivos multimedia subidos por usuarios (ignorado en Git)
│   ├── avatars/
│   ├── pets/
│   └── posts/
├── static/                       # Recursos estáticos fuente durante el desarrollo
│   ├── css/                      # Hojas de estilo CSS del frontend
│   ├── js/                       # Scripts JavaScript del cliente
│   └── img/                      # Logotipos, íconos y gráficos estáticos del sistema
├── templates/                    # Plantillas globales y componentes compartidos
│   ├── base.html                 # Plantilla maestra con estructura HTML5 compartida
│   ├── components/               # Componentes reutilizables (navbar, footer, cards, alertas)
│   └── layouts/                  # Diseños de página base (feed, perfil, auth)
├── .editorconfig                 # Reglas automáticas de formato e indentación
├── .env.dev                      # Variables de entorno para desarrollo local
├── .gitignore                    # Reglas de exclusión de Git
├── manage.py                     # Utilidad de línea de comandos de Django
└── requirements.txt              # Dependencias de Python del proyecto
```

> [!NOTE]
> La carpeta `apps/<module_name>/` en este diagrama funciona como **plantilla de referencia arquitectónica**. Ninguna aplicación ha sido creada aún en el proyecto.

### Principios de la arquitectura modular

| Carpeta | Propósito | Reglas de configuración |
| :--- | :--- | :--- |
| `apps/` | Aloja los dominios de negocio separados en submódulos independientes | Cada app configurará su clase en `apps.py` con `name = 'apps.<nombre_app>'` para su registro limpio en `INSTALLED_APPS`. |
| `templates/` | Plantilla base global y componentes de interfaz reutilizables | Las plantillas maestras y componentes globales van en la raíz (`templates/base.html`, `templates/components/`), mientras que las vistas específicas de módulo van en `apps/<nombre_app>/templates/<nombre_app>/`. |
| `static/` | Archivos CSS, JavaScript e imágenes estáticas del sistema | Carpeta fuente conectada a Django mediante `STATICFILES_DIRS = [BASE_DIR / 'static']`. En producción, `collectstatic` compila en `staticfiles/`. |
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
> **Nota sobre los identificadores únicos:**
> La forma exacta de generar el identificador único final (sea mediante marca de tiempo `timestamp`, UUIDv4, hash criptográfico o combinaciones de los mismos) **aún no está fijada de manera definitiva**. Los patrones y sufijos mostrados en la tabla anterior son **ejemplos ilustrativos** para modelar el principio de diseño: que el propio nombre del archivo identifique con certeza quién es el usuario propietario y a qué recurso pertenece.

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
  - Nombres de funciones, clases y rutas en inglés (ejemplo: `name='pet-list'`, `name='pet-detail'`).
  - Mantener las vistas delgadas delegando la lógica de negocio a modelos o capas de servicio.
- **Plantillas HTML:**
  - Estructura semántica HTML5 heredando de `base.html`.
