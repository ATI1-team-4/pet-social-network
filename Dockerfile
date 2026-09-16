# Imagen base oficial de Python ligera para desarrollo
FROM python:3.12-slim

# Evitar la generación de archivos .pyc y asegurar la salida inmediata de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias de Python y precargar binario de Tailwind
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    && (tailwindcss --help > /dev/null 2>&1 || true)


# Copiar el código de la aplicación
COPY . /app/

# Compilar Tailwind CSS para asegurar que el archivo exista en la imagen
RUN tailwindcss -i theme/static_src/src/styles.css -o theme/static/css/dist/styles.css --minify

# Exponer el puerto de desarrollo de Django
EXPOSE 8000

# Iniciar el servidor de desarrollo escuchando en todas las interfaces
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
