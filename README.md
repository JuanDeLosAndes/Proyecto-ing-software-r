# Sistema de Asignacion de Salones — Universidad Catalica de Colombia

Sistema web de gestion academica de espacios fisicos con optimizacion genetica.  
Desarrollado con FastAPI, SQLModel, Jinja2 y SQLite.

---

## Tecnologias

| Capa | Tecnologia |
|---|---|
| Backend | FastAPI + SQLModel + Pydantic |
| Base de datos | SQLite (local) |
| Frontend | Jinja2 + HTML/CSS/JS vanilla |
| Algoritmo | Algoritmo genetico (Python puro) |
| Testing | pytest + FastAPI TestClient |

---

## Instalacion y ejecucion local

### 1. Clonar el repositorio

```bash
git clone https://github.com/<tu-usuario>/PROYECTO-ING-SOFTWARE-R.git
cd PROYECTO-ING-SOFTWARE-R
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Variables de entorno (opcional)

Crea un archivo `.env` en la raiz (no se sube al repo por el `.gitignore`):

```env
# Base de datos — por defecto usa SQLite local
DATABASE_URL=sqlite:///database.db

# Para Azure SQL (produccion):
# DATABASE_URL=mssql+pyodbc://user:pass@server.database.windows.net/db?driver=ODBC+Driver+18+for+SQL+Server

# Puerto del servidor
PORT=8000
```

### 5. Ejecutar la aplicacion

```bash
uvicorn main:app --reload --port 8000
```

Abre `http://localhost:8000` en el navegador.

> La aplicacion crea las tablas y siembra los datos base (roles, salones, 20 materias) automaticamente al iniciar. No se necesita correr migraciones manualmente.

---

## Ejecutar pruebas automatizadas

```bash
# Todas las pruebas
pytest

# Con detalle completo
pytest -v

# Un archivo especifico
pytest tests/test_usuarios.py -v

# Una prueba especifica
pytest tests/test_inscripciones.py::TestInscripcion::test_inscripcion_semestre_insuficiente_400 -v

# Con reporte de cobertura (requiere: pip install pytest-cov)
pytest --cov=. --cov-report=term-missing
```

---

## Estructura del proyecto