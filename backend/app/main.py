"""
Servidor API REST FastAPI — Sistema SIAE-Vetanco
[RF-19 a RF-29]
Provee los endpoints para el Dashboard Ejecutivo, Visor Split-View,
Auditoría 1-Click con Audit Trail, Centro Batch SAP e Importación de OCs.
"""
import asyncio
import csv
import io
import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.config import settings, DATA_DIR, PDF_STORAGE_DIR
from app.database import init_db, get_db
from app.models import (
    Comprobante,
    ComprobanteItem,
    AuditoriaLog,
    LoteBatch,
    Proveedor,
    OrdenCompra,
    OrdenCompraItem,
    EstadoComprobante,
    TipoDisparoBatch
)
from app.schemas import (
    ComprobanteResponse,
    ComprobanteUpdate,
    RechazoComprobante,
    DashboardMetrics,
    LoteBatchResponse,
    OrdenCompraResponse,
    ProveedorResponse
)
from app.modules.mail_ingestor import procesar_comprobante_pdf, ejecutar_ingesta_automatica
from app.modules.batch_exporter import generar_lote_batch_sap
from app.modules.scheduler import iniciar_scheduler, detener_scheduler
from app.modules.validators import a_decimal, validar_consistencia_impositiva

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("siae.api")

# Control de inactividad y auto-shutdown al cerrar navegador
_last_heartbeat_time = None
_client_connected = False
_shutdown_task = None


def _cerrar_todo():
    """Finaliza limpiamente los servidores (FastAPI y Vite) cuando el usuario cierra la interfaz."""
    logger.info("Cerrando SIAE-Vetanco completamente...")
    try:
        if os.name == "nt":
            # Si Vite está corriendo en el puerto 5173, cerrarlo también
            cmd = "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :5173') do taskkill /f /pid %a"
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.warning(f"Error al limpiar procesos secundarios: {e}")
    os._exit(0)


async def _watchdog_inactividad():
    """Monitorea que haya al menos una pestaña de navegador activa."""
    global _last_heartbeat_time, _client_connected
    # Período de gracia inicial de 35s para dar tiempo al navegador a iniciar y enviar su primer ping
    await asyncio.sleep(35)
    while True:
        await asyncio.sleep(2)
        if _client_connected and _last_heartbeat_time:
            # Si pasaron más de 6 segundos sin latidos, cerrar el sistema
            if time.time() - _last_heartbeat_time > 6.0:
                logger.info("No se detectó actividad del navegador en los últimos 6 segundos. Cerrando sistema...")
                _cerrar_todo()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización de tablas y tareas en segundo plano
    logger.info("Iniciando backend SIAE-Vetanco...")
    init_db()
    iniciar_scheduler()
    watchdog = asyncio.create_task(_watchdog_inactividad())
    yield
    # Parada ordenada
    watchdog.cancel()
    detener_scheduler()
    logger.info("Backend SIAE-Vetanco detenido.")


app = FastAPI(
    title="SIAE-Vetanco API",
    description="Sistema Inteligente de Automatización y Extracción de Facturas de Proveedores para SAP S/4HANA",
    version="1.0.0",
    lifespan=lifespan
)

# Habilitar CORS para permitir conexión desde el Frontend en Vite (http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/system/heartbeat")
async def sistema_heartbeat():
    """Recibe pings periódicos del navegador para constatar que la pestaña sigue abierta."""
    global _last_heartbeat_time, _client_connected, _shutdown_task
    _last_heartbeat_time = time.time()
    _client_connected = True
    # Si había una cuenta regresiva de shutdown pendiente (ej: por recarga F5), cancelarla
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
        _shutdown_task = None
    return {"status": "alive", "timestamp": _last_heartbeat_time}


async def _ejecutar_shutdown_con_gracia(segundos: float = 2.5):
    try:
        await asyncio.sleep(segundos)
        _cerrar_todo()
    except asyncio.CancelledError:
        logger.info("Shutdown cancelado por recarga o reconexión de página.")


@app.post("/api/system/shutdown")
async def sistema_shutdown():
    """Señal de cierre inmediato enviada por el navegador (evento beforeunload)."""
    global _shutdown_task
    logger.info("Señal de cierre recibida desde el navegador. Iniciando conteo de gracia...")
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
    _shutdown_task = asyncio.create_task(_ejecutar_shutdown_con_gracia(2.5))
    return {"status": "shutting_down", "grace_seconds": 2.5}


# =====================================================================
# 1. Dashboard Ejecutivo & Métricas (RF-19)
# =====================================================================

@app.get("/api/dashboard/resumen", response_model=DashboardMetrics)
def obtener_metricas_dashboard(db: Session = Depends(get_db)):
    """[RF-19] Devuelve los indicadores operativos del día para el analista contable."""
    hoy = date.today()

    total_recibidas = db.query(Comprobante).filter(
        func.date(Comprobante.fecha_creacion) == hoy
    ).count()

    # Si en la demo no hay facturas con fecha_creacion de hoy, tomamos el total general
    if total_recibidas == 0:
        total_recibidas = db.query(Comprobante).count()

    stp_automaticas = db.query(Comprobante).filter(
        Comprobante.estado.in_([
            EstadoComprobante.PROCESADA_LISTA_BATCH,
            EstadoComprobante.CONSOLIDADA_EN_BATCH
        ]),
        Comprobante.confianza_global >= settings.CONFIDENCE_THRESHOLD,
        Comprobante.motivo_rechazo.is_(None)
    ).count()

    pendientes_auditoria = db.query(Comprobante).filter(
        Comprobante.estado == EstadoComprobante.REQUIERE_AUDITORIA
    ).count()

    aprobadas_pendientes_lote = db.query(Comprobante).filter(
        Comprobante.estado.in_([
            EstadoComprobante.PROCESADA_LISTA_BATCH,
            EstadoComprobante.APROBADA_POR_USUARIO
        ]),
        Comprobante.lote_batch_id.is_(None)
    ).count()

    rechazadas = db.query(Comprobante).filter(
        Comprobante.estado == EstadoComprobante.RECHAZADA
    ).count()

    # Cálculo de montos pendientes de consolidar en lote
    comprobantes_lote = db.query(Comprobante).filter(
        Comprobante.estado.in_([
            EstadoComprobante.PROCESADA_LISTA_BATCH,
            EstadoComprobante.APROBADA_POR_USUARIO
        ]),
        Comprobante.lote_batch_id.is_(None)
    ).all()

    monto_ars = sum(c.importe_total for c in comprobantes_lote if c.moneda != "USD")
    monto_usd = sum(c.importe_total for c in comprobantes_lote if c.moneda == "USD")

    total_lotes = db.query(LoteBatch).count()
    porcentaje_stp = round((stp_automaticas / total_recibidas * 100.0), 1) if total_recibidas > 0 else 0.0

    return DashboardMetrics(
        total_recibidas_hoy=total_recibidas,
        stp_automaticas=stp_automaticas,
        porcentaje_stp=porcentaje_stp,
        pendientes_auditoria=pendientes_auditoria,
        aprobadas_pendientes_lote=aprobadas_pendientes_lote,
        rechazadas=rechazadas,
        monto_lote_ars=a_decimal(monto_ars),
        monto_lote_usd=a_decimal(monto_usd),
        total_lotes_historicos=total_lotes
    )


# =====================================================================
# 2. Listado y Filtros Históricos (RF-24)
# =====================================================================

@app.get("/api/comprobantes", response_model=List[ComprobanteResponse])
def listar_comprobantes(
    cuit_emisor: Optional[str] = Query(None),
    estado: Optional[EstadoComprobante] = Query(None),
    orden_compra: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """[RF-24] Búsqueda y filtrado multicriterio de comprobantes en Staging."""
    query = db.query(Comprobante).order_by(desc(Comprobante.fecha_creacion))

    if cuit_emisor:
        query = query.filter(Comprobante.cuit_emisor.contains(cuit_emisor.strip()))
    if estado:
        query = query.filter(Comprobante.estado == estado)
    if orden_compra:
        query = query.filter(Comprobante.orden_compra_nro.contains(orden_compra.strip()))
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Comprobante.razon_social_emisor.ilike(s),
                Comprobante.cuit_emisor.ilike(s),
                Comprobante.cae.ilike(s),
                Comprobante.orden_compra_nro.ilike(s)
            )
        )

    return query.all()


@app.get("/api/comprobantes/{comprobante_id}", response_model=ComprobanteResponse)
def obtener_comprobante(comprobante_id: str, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un comprobante con ítems y auditoría."""
    comp = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return comp


@app.delete("/api/comprobantes/{comprobante_id}")
def eliminar_comprobante(comprobante_id: str, db: Session = Depends(get_db)):
    """
    [Demostración y Limpieza]
    Elimina un comprobante de la base de datos de Staging junto con sus ítems y logs.
    Permite remover facturas ya analizadas para volver a probarlas en presentaciones.
    """
    comp = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    # Intentar eliminar el archivo PDF físico asociado si existe
    try:
        if comp.archivo_pdf_path and os.path.exists(comp.archivo_pdf_path):
            os.remove(comp.archivo_pdf_path)
    except Exception as e:
        logger.warning(f"No se pudo eliminar el archivo PDF físico {comp.archivo_pdf_path}: {e}")

    db.delete(comp)
    db.commit()
    return {"ok": True, "mensaje": f"Comprobante {comprobante_id} eliminado exitosamente"}


# =====================================================================
# 3. Visor de PDF para Split-View (RF-20, RNF-04)
# =====================================================================

@app.get("/api/comprobantes/{comprobante_id}/pdf")
def descargar_visor_pdf(
    comprobante_id: str,
    descargar: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    [RF-20] Retorna el stream seguro del PDF.
    Si descargar=False (por defecto), envía 'inline' para visualización en iframe sin descarga forzada.
    Si descargar=True, envía 'attachment' para guardar el archivo.
    """
    comp = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    ruta = Path(comp.archivo_pdf_path)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en el servidor")

    disposition = "attachment" if descargar else "inline"
    filename = f"Factura_{comp.razon_social_emisor}_{comp.punto_venta:04d}-{comp.numero_comprobante:08d}.pdf"

    return FileResponse(
        path=str(ruta),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'}
    )


# =====================================================================
# 4. Ingesta Manual y Sincronización (RF-01, RF-02)
# =====================================================================

@app.post("/api/comprobantes/subir-pdf", response_model=ComprobanteResponse)
async def subir_comprobante_manual(
    file: UploadFile = File(...),
    remitente: Optional[str] = Form("analista.manual@vetanco.com"),
    db: Session = Depends(get_db)
):
    """Permite al analista arrastrar y subir una factura PDF directamente desde la interfaz."""
    contenido = await file.read()
    simulated_msg_id = f"UPLOAD_{file.filename}_{len(contenido)}_{datetime.now().timestamp()}"

    ok, mensaje, comp = procesar_comprobante_pdf(
        db=db,
        pdf_bytes=contenido,
        nombre_archivo_original=file.filename,
        message_id=simulated_msg_id,
        remitente=remitente,
        asunto=f"Carga manual: {file.filename}"
    )

    if not ok:
        raise HTTPException(status_code=400, detail=mensaje)

    return comp


@app.post("/api/ingestor/sincronizar")
def sincronizar_correos_ahora(db: Session = Depends(get_db)):
    """Dispara inmediatamente el escaneo de Gmail / bandeja local."""
    resultado = ejecutar_ingesta_automatica(db)
    return {"status": "ok", "resultado": resultado}


# =====================================================================
# 5. Auditoría 1-Click y Rechazo de Facturas (RF-21, RF-22, RF-23)
# =====================================================================

@app.put("/api/comprobantes/{comprobante_id}/aprobar", response_model=ComprobanteResponse)
def aprobar_comprobante_1click(
    comprobante_id: str,
    datos: ComprobanteUpdate,
    db: Session = Depends(get_db)
):
    """
    [RF-22, RF-23]
    Permite al analista corregir campos numéricos o de cabecera en el panel derecho del Split-View,
    recalcula la consistencia impositiva, registra el Audit Trail y aprueba el comprobante
    para su inclusión en el siguiente lote Batch SAP.
    """
    comp = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    usuario = datos.usuario or "analista.contable"
    cambios_realizados = []

    # Comparar campos actualizados para registrar en AuditoriaLog (RF-23)
    campos_a_verificar = [
        ("punto_venta", datos.punto_venta),
        ("numero_comprobante", datos.numero_comprobante),
        ("cae", datos.cae),
        ("orden_compra_nro", datos.orden_compra_nro),
        ("neto_gravado_21", datos.neto_gravado_21),
        ("neto_gravado_105", datos.neto_gravado_105),
        ("neto_gravado_27", datos.neto_gravado_27),
        ("iva_21", datos.iva_21),
        ("iva_105", datos.iva_105),
        ("percepcion_iibb", datos.percepcion_iibb),
        ("percepcion_iibb_jurisdiccion", datos.percepcion_iibb_jurisdiccion),
        ("importe_total", datos.importe_total)
    ]

    for nombre_campo, nuevo_val in campos_a_verificar:
        if nuevo_val is not None:
            val_actual = getattr(comp, nombre_campo)
            if str(val_actual) != str(nuevo_val):
                cambios_realizados.append((nombre_campo, str(val_actual), str(nuevo_val)))
                setattr(comp, nombre_campo, nuevo_val)

    # Validar consistencia matemática de la corrección
    subtotales_dict = {
        "neto_gravado_21": comp.neto_gravado_21,
        "neto_gravado_105": comp.neto_gravado_105,
        "neto_gravado_27": comp.neto_gravado_27,
        "no_gravado": comp.no_gravado,
        "exento": comp.exento,
        "iva_21": comp.iva_21,
        "iva_105": comp.iva_105,
        "iva_27": comp.iva_27,
        "percepcion_iibb": comp.percepcion_iibb,
        "percepcion_iva": comp.percepcion_iva,
        "impuestos_internos": comp.impuestos_internos,
        "importe_total": comp.importe_total
    }
    suma_ok, total_calc, _, alertas_suma = validar_consistencia_impositiva(subtotales_dict)
    if not suma_ok:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede aprobar: la suma matemática calculada (${total_calc}) no coincide con el total (${comp.importe_total})"
        )

    # Limpiar alertas impositivas resueltas
    comp.alertas_validacion = [
        a for a in comp.alertas_validacion
        if a.get("codigo") != "DISCREPANCIA_SUMA_IMPOSITIVA"
    ]

    # Transición de estado (RF-18)
    comp.estado = EstadoComprobante.APROBADA_POR_USUARIO
    comp.confianza_global = 1.0  # Homologado al 100% por supervisión humana

    # Registrar en AuditoriaLog (RF-23)
    for campo, antes, despues in cambios_realizados:
        log = AuditoriaLog(
            comprobante_id=comp.id,
            usuario=usuario,
            accion="EDICION_CAMPO",
            campo_modificado=campo,
            valor_anterior=antes,
            valor_nuevo=despues,
            detalles=f"Corrección manual en formulario Split-View por {usuario}"
        )
        db.add(log)

    log_aprobacion = AuditoriaLog(
        comprobante_id=comp.id,
        usuario=usuario,
        accion="APROBACION_1CLICK",
        campo_modificado="estado",
        valor_anterior="REQUIERE_AUDITORIA",
        valor_nuevo="APROBADA_POR_USUARIO",
        detalles="Aprobación definitiva 1-Click para inclusión en lote SAP"
    )
    db.add(log_aprobacion)

    db.commit()
    db.refresh(comp)
    return comp


@app.put("/api/comprobantes/{comprobante_id}/rechazar", response_model=ComprobanteResponse)
def rechazar_comprobante(
    comprobante_id: str,
    datos: RechazoComprobante,
    db: Session = Depends(get_db)
):
    """[RF-22, RF-23] Rechaza el comprobante con motivo documentado y trazabilidad."""
    comp = db.query(Comprobante).filter(Comprobante.id == comprobante_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    estado_anterior = comp.estado.value
    comp.estado = EstadoComprobante.RECHAZADA
    comp.motivo_rechazo = datos.motivo

    log = AuditoriaLog(
        comprobante_id=comp.id,
        usuario=datos.usuario or "analista.contable",
        accion="RECHAZO",
        campo_modificado="estado",
        valor_anterior=estado_anterior,
        valor_nuevo="RECHAZADA",
        detalles=f"Motivo de rechazo: {datos.motivo}"
    )
    db.add(log)
    db.commit()
    db.refresh(comp)
    return comp


# =====================================================================
# 6. Centro de Lotes Batch SAP (RF-26, RF-27, RF-28, RF-29)
# =====================================================================

@app.post("/api/batch/generar", response_model=LoteBatchResponse)
def generar_lote_manual(db: Session = Depends(get_db)):
    """[RF-26] Genera el archivo CSV para SAP S/4HANA bajo demanda."""
    ok, mensaje, lote = generar_lote_batch_sap(db, TipoDisparoBatch.MANUAL)
    if not ok or not lote:
        raise HTTPException(status_code=400, detail=mensaje)
    return lote


@app.get("/api/batch", response_model=List[LoteBatchResponse])
def listar_lotes_batch(db: Session = Depends(get_db)):
    """Lista todos los lotes batch generados históricamente."""
    return db.query(LoteBatch).order_by(desc(LoteBatch.fecha_generacion)).all()


@app.get("/api/batch/{lote_id}/descargar")
def descargar_archivo_batch(lote_id: int, db: Session = Depends(get_db)):
    """[RF-29] Descarga el archivo plano CSV homologado para carga masiva en SAP."""
    lote = db.query(LoteBatch).filter(LoteBatch.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    ruta = Path(lote.ruta_archivo)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo físico de lote no encontrado")

    return FileResponse(
        path=str(ruta),
        media_type="text/csv",
        filename=lote.nombre_archivo
    )


@app.get("/api/batch/{lote_id}/preview")
def previsualizar_lote(lote_id: int, db: Session = Depends(get_db)):
    """Permite al analista ver las líneas BKPF y BSEG en la pantalla de la WebApp."""
    lote = db.query(LoteBatch).filter(LoteBatch.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    ruta = Path(lote.ruta_archivo)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado")

    contenido = ruta.read_text(encoding="utf-8")
    return {
        "lote_id": lote.id,
        "nombre_archivo": lote.nombre_archivo,
        "sha256": lote.sha256_hash,
        "contenido": contenido,
        "lineas": contenido.strip().split("\r\n")
    }


# =====================================================================
# 7. Órdenes de Compra y Proveedores (Cierre Observación #12)
# =====================================================================

@app.get("/api/ordenes-compra", response_model=List[OrdenCompraResponse])
def listar_ordenes_compra(db: Session = Depends(get_db)):
    """Lista las Órdenes de Compra abiertas en Staging para el 3-Way Matching."""
    return db.query(OrdenCompra).all()


@app.post("/api/ordenes-compra/importar-csv")
async def importar_maestro_oc_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    [Cierre Observación #12]
    Permite cargar el reporte maestro semanal de Órdenes de Compra exportado de SAP S/4HANA
    para que SIAE tenga contra qué validar precios y saldos remanentes estando 100% desacoplado.
    """
    contenido = await file.read()
    texto = contenido.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(texto), delimiter=";")

    cargadas = 0
    for fila in reader:
        numero_oc = fila.get("numero_oc") or fila.get("EBELN")
        cuit_prov = fila.get("cuit_proveedor") or fila.get("LIFNR")
        if not numero_oc or not cuit_prov:
            continue

        cuit_limpio = cuit_prov.replace("-", "").strip()
        oc = db.query(OrdenCompra).filter(OrdenCompra.numero_oc == numero_oc).first()
        if not oc:
            # Asegurar existencia del proveedor
            prov = db.query(Proveedor).filter(Proveedor.cuit == cuit_limpio).first()
            if not prov:
                prov = Proveedor(
                    cuit=cuit_limpio,
                    razon_social=fila.get("razon_social", "PROVEEDOR SAP"),
                    codigo_acreedor_sap=f"PROV_{cuit_limpio}",
                    planta_default="PL01"
                )
                db.add(prov)
                db.flush()

            oc = OrdenCompra(
                numero_oc=numero_oc,
                cuit_proveedor=cuit_limpio,
                estado=fila.get("estado", "ABIERTA"),
                moneda=fila.get("moneda", "ARS"),
                centro_costo=fila.get("centro_costo", "PL01")
            )
            db.add(oc)
            db.flush()

        # Agregar ítem si está especificado
        cod_insumo = fila.get("codigo_insumo") or fila.get("MATNR")
        if cod_insumo:
            item_existente = db.query(OrdenCompraItem).filter(
                OrdenCompraItem.numero_oc == numero_oc,
                OrdenCompraItem.codigo_insumo == cod_insumo
            ).first()
            if not item_existente:
                item_oc = OrdenCompraItem(
                    numero_oc=numero_oc,
                    posicion_sap=fila.get("posicion_sap", "00010"),
                    codigo_insumo=cod_insumo,
                    descripcion=fila.get("descripcion", "Materia Prima"),
                    cantidad_pedida=float(fila.get("cantidad_pedida", 100.0)),
                    cantidad_remanente=float(fila.get("cantidad_remanente", 100.0)),
                    unidad_medida=fila.get("unidad_medida", "KG"),
                    precio_unitario=a_decimal(fila.get("precio_unitario", 1000.0)),
                    cuenta_contable_sap=fila.get("cuenta_contable", "11040010"),
                    indicador_iva_sap=fila.get("indicador_iva", "V1")
                )
                db.add(item_oc)
        cargadas += 1

    db.commit()
    return {"status": "ok", "filas_procesadas": cargadas}


@app.get("/api/proveedores", response_model=List[ProveedorResponse])
def listar_proveedores(db: Session = Depends(get_db)):
    """Lista los 20 proveedores recurrentes registrados en Staging."""
    return db.query(Proveedor).all()


# Montar la aplicación React compilada (frontend/dist) para servirla directamente en http://localhost:8000
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
