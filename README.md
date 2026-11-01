# SIAE-Vetanco
### Sistema Inteligente de Automatización y Enlace de Facturas de Proveedores para SAP S/4HANA

> **Universidad Argentina de la Empresa (UADE)**  
> **Materia:** Dirección de Proyectos Informáticos  
> **Año:** 2026 — Segundo Cuatrimestre  
> **Proyecto:** Trabajo Práctico Obligatorio (TPO) — Vetanco S.A.

---

## 📌 Descripción del Proyecto

**SIAE-Vetanco** es una solución integral diseñada para automatizar la recepción, extracción fiscal, validación por triple concordancia (*3-Way Matching*) y exportación desacoplada de facturas de proveedores hacia el sistema ERP central **SAP S/4HANA** de Vetanco S.A.

El sistema resuelve el cuello de botella manual del departamento de Cuentas a Pagar:
* Elimina la carga manual repetitiva de comprobantes.
* Detecta discrepancias de precios, cantidades e inconsistencias impositivas AFIP/ARCA de forma temprana.
* Automatiza la generación del lote contable diario consolidado (*batch*) listo para ingesta vía BAPI / LSMW.

---

## 🚀 Arquitectura y Capacidades Principales

### 1. Ingesta Multicanal y Motor de Extracción Híbrido
* **Ingesta Automática:** Monitoreo periódico por IMAP (casilla de correo de proveedores) con soporte para subida manual vía Drag & Drop y simulación local.
* **Filtro Anti-Spam Fiscal:** Detección y descarte de archivos adjuntos no fiscales antes del procesamiento.
* **Extracción Determinística Local:** Procesamiento sub-segundo con `pdfplumber` y `PyMuPDF` mediante expresiones regulares especializadas en regímenes fiscales argentinos (facturas A, B, C, M, Notas de Crédito/Débito, MiPyMEs).
* **Extracción Asistida por IA Quirúrgica:** En comprobantes con formatos no estructurados o complejos, activa como fallback el modelo **Google Gemini (`gemini-2.5-flash`)** para garantizar una precisión superior al 95%.

### 2. Motor de Validación y 3-Way Matching (RF-14 a RF-18)
* **Validación Impositiva Matemática:** Comprobación estricta de que $\sum \text{Neto Gravado} + \text{IVA (21\%, 10.5\%, 27\%)} + \text{Percepciones (IIBB, Ganancias)} - \text{No Gravados} = \text{Total Comprobante}$ con tolerancia de centavos.
* **Triple Concordancia con SAP:** Comparación ítem por ítem entre la factura recibida y la Orden de Compra (OC) registrada en SAP.
* **Clasificación por Tolerancias:**
  * **STP (*Straight-Through Processing*):** Diferencia menor o igual a \$1.000 ARS y tolerancias de cantidad/precio válidas. Pasa directo a lote sin intervención humana.
  * **DISCREPANCIA_MENOR / DISCREPANCIA_MAYOR:** Alerta por diferencias de precio unitario, ítems no contenidos en la OC o montos que exceden los umbrales configurados.

### 3. Interfaz de Usuario y Auditoría 1-Click (RF-19 a RF-24)
* **Dashboard Ejecutivo en Tiempo Real:** Métricas operativas diarias (total comprobantes recibidos, procesados STP, pendientes de revisión, alertas críticas y monto acumulado).
* **Visor Split-View:** Visualización simultánea del PDF original al lado de los campos fiscales estructurados y tabla de ítems con capacidad de edición en vivo.
* **Audit Trail Inmutable:** Registro de cada cambio manual o aprobación con usuario, timestamp y valor anterior/nuevo.

### 4. Centro de Lotes Batch SAP y Notificaciones (RF-25 a RF-29)
* **Generación Diaria Automatizada:** A las 17:00 hs (vía cron APScheduler) o por disparo manual.
* **Formato Estricto BAPI / LSMW:** Exportación desacoplada en texto plano UTF-8 sin BOM delimitado por punto y coma (`;`), compatible con estructuras estándar de SAP.
* **Notificaciones por Email:** Envío automático del resumen de lote y detalle consolidado al analista y jefatura de cuentas a pagar.

### 5. Lanzador Silencioso Desktop 1-Click
* Ejecución transparente en segundo plano (0 ventanas de consola) con `pythonw` y sincronización activa de puertos.
* Cierre automático de procesos en 2.5 segundos al cerrar la pestaña o ventana del navegador.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy ORM, SQLite, Pydantic v2, APScheduler |
| **Parsing & IA** | PyMuPDF (fitz), pdfplumber, Google Gemini API (`google-genai` / `gemini-2.5-flash`) |
| **Frontend** | React 18, Vite 5, Tailwind CSS, Lucide Icons |
| **Testing** | pytest, pytest-asyncio, Starlette TestClient (18/18 pruebas automatizadas) |
| **Despliegue** | VBScript / Python Launcher nativo Windows, Docker & Docker Compose |

---

## 📂 Estructura del Repositorio

```text
SIAE-Vetanco/
├── Iniciar SIAE.vbs             # Acceso directo 1-Click silencioso para Windows
├── iniciar_siae.bat             # Script batch de inicio rápido y configuración
├── iniciar_siae.ps1             # Script PowerShell para entornos corporativos
├── launcher.py                  # Lanzador maestro con sincronización y auto-shutdown
├── docker-compose.yml           # Configuración multi-contenedor Docker
│
├── backend/                     # API REST FastAPI & Motores de negocio
│   ├── app/
│   │   ├── main.py              # Endpoints REST y ciclo de vida (lifespan)
│   │   ├── config.py            # Configuración por variables de entorno (.env)
│   │   ├── database.py          # Conexión SQLAlchemy y sesiones SQLite/Postgres
│   │   ├── models.py            # Modelos de datos relacionales
│   │   ├── schemas.py           # Esquemas Pydantic para validación y serialización
│   │   └── modules/
│   │       ├── mail_ingestor.py     # Ingestor IMAP y orquestador de comprobantes
│   │       ├── extractor.py         # Extractor determinístico por regex y layout
│   │       ├── gemini_extractor.py  # Extractor asistido por Google Gemini
│   │       ├── validators.py        # Validaciones impositivas y 3-Way Matching
│   │       ├── batch_exporter.py    # Generador de archivos batch BAPI/LSMW para SAP
│   │       ├── notification.py      # Notificador SMTP para cierres de lote
│   │       └── scheduler.py         # Programador APScheduler para tareas cron
│   ├── data/
│   │   ├── maestro_oc_sap.csv       # Catálogo maestro de OCs de ejemplo
│   │   └── sample_pdfs/             # Comprobantes muestra para pruebas
│   ├── scripts/                     # Scripts de prueba, siembra y auditoría masiva
│   │   └── seed_demo.py             # Carga inicial de datos demo y OCs
│   ├── tests/                       # Suite de pruebas unitarias y de integración
│   │   ├── test_api.py
│   │   ├── test_batch_and_ingestor.py
│   │   ├── test_extractor.py
│   │   └── test_validators.py
│   ├── requirements.txt         # Dependencias Python
│   └── .env.example             # Plantilla de variables de entorno
│
├── frontend/                    # Single Page Application React + Vite
│   ├── src/
│   │   ├── App.jsx              # Componente principal con heartbeat y auto-shutdown
│   │   ├── api.js               # Cliente de consumo de la API REST
│   │   └── components/
│   │       ├── ExecutiveDashboard.jsx   # Métricas y KPIs operativos
│   │       ├── InvoiceTable.jsx         # Tabla y filtros de comprobantes
│   │       ├── SplitViewAuditor.jsx     # Visor split-view PDF + formulario
│   │       ├── BatchCenterModal.jsx     # Gestión de lotes diarios SAP
│   │       ├── ImportOCModal.jsx        # Importación masiva de OCs
│   │       └── UploadInvoiceModal.jsx   # Subida manual de facturas
│   ├── package.json             # Dependencias Node.js
│   └── vite.config.js           # Configuración de Vite y proxy reverso
│
└── TP Facturas/                 # Repositorio de comprobantes reales evaluados
```

---

## ⚙️ Instalación y Puesta en Marcha

### Prerrequisitos
* **Python 3.10 o superior**
* **Node.js 18 o superior**

### Modo Recomendado: 1-Click (Windows)
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/franconferreira/SIAE-Vetanco.git
   cd SIAE-Vetanco
   ```
2. Configurar el archivo de entorno en `backend/.env` (tomando como base `backend/.env.example`).
3. Hacer doble clic en **`iniciar_siae.bat`** (o en **`Iniciar SIAE.vbs`**).
   * La primera ejecución creará el entorno virtual (`venv`), instalará las librerías necesarias y abrirá automáticamente el navegador en `http://localhost:5173`.
   * Al cerrar la pestaña del navegador, todos los servicios se detendrán automáticamente en 2.5 segundos.

---

### Modo Manual

#### 1. Backend
```bash
cd backend
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python scripts/seed_demo.py
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
La aplicación estará disponible en `http://localhost:5173`.

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto cuenta con cobertura de pruebas automatizadas sobre extracción, validaciones impositivas, concordancia 3-Way Matching, generación batch y endpoints de la API:

```bash
cd backend
.\venv\Scripts\pytest -v
```

Resultado esperado:
```text
tests/test_api.py ............                                      [ 33%]
tests/test_batch_and_ingestor.py ....                               [ 55%]
tests/test_extractor.py ...                                         [ 72%]
tests/test_validators.py .....                                      [100%]
============================== 18 passed in ~12s ===============================
```

---

## 👥 Autores y Créditos
* **Franco Ferreira** — Desarrollo e Implementación
* Cátedra de **Dirección de Proyectos Informáticos** — UADE (2026)
