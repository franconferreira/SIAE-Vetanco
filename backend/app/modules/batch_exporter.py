"""
Módulo 5: Generador y Exportador de Lotes Batch para SAP S/4HANA
[RF-25 a RF-29]
1. Consolidación automática diaria (17:00 hs) o manual on-demand desde la web.
2. Formato estricto delimitado por ';' en UTF-8 sin BOM (compatible BAPI / LSMW).
3. Registros Tipo 01 (BKPF - Cabecera) y Tipo 02 (BSEG - Posición Acreedor 31 y Gasto/OC 40).
4. Generación de Hash SHA-256 del archivo y actualización de estado a CONSOLIDADA_EN_BATCH.
5. Notificación automática por SMTP y guardado de reporte en data/notificaciones/.
"""
import hashlib
import logging
import re
import smtplib
from datetime import datetime, date
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings, BATCH_OUTPUT_DIR, NOTIFICATIONS_DIR
from app.models import (
    Comprobante,
    ComprobanteItem,
    EstadoComprobante,
    LoteBatch,
    TipoDisparoBatch,
    Proveedor,
    OrdenCompraItem
)
from app.modules.validators import a_decimal, limpiar_cuit

logger = logging.getLogger("siae.batch")


def formatear_fecha_sap(f: Optional[date]) -> str:
    """Convierte una fecha a formato estándar SAP AAAAMMDD."""
    if not f:
        return datetime.today().strftime("%Y%m%d")
    return f.strftime("%Y%m%d")


def enviar_notificacion_cierre_lote(lote: LoteBatch, pendientes_count: int = 0) -> str:
    """
    [RF-28] Dispara correo electrónico de resumen al analista y guarda copia en archivo local.
    """
    NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    fecha_str = lote.fecha_generacion.strftime("%d/%m/%Y %H:%M:%S")

    cuerpo = (
        f"====================================================================\n"
        f"REPORTE OFICIAL DE CIERRE DE LOTE BATCH — SIAE-VETANCO\n"
        f"Exportación para Importación Masiva en SAP S/4HANA (BAPI / LSMW)\n"
        f"====================================================================\n\n"
        f"ID de Lote: #{lote.id}\n"
        f"Nombre de Archivo: {lote.nombre_archivo}\n"
        f"Fecha y Hora de Generación: {fecha_str}\n"
        f"Tipo de Disparo: {lote.tipo_disparo.value}\n"
        f"Firma Criptográfica SHA-256: {lote.sha256_hash}\n\n"
        f"RESUMEN CONTABLE:\n"
        f"- Facturas Consolidadas: {lote.cantidad_facturas}\n"
        f"- Total Lote en Pesos (ARS): $ {lote.total_ars:,.2f}\n"
        f"- Total Lote en Dólares (USD): USD$ {lote.total_usd:,.2f}\n"
        f"- Facturas Pendientes de Auditoría para Mañana: {pendientes_count}\n\n"
        f"ESTADO DE OPERACIÓN:\n"
        f"El archivo está disponible para descarga y procesamiento manual por el\n"
        f"Analista de Cuentas a Pagar en cumplimiento de la política de seguridad.\n"
    )

    # 1. Guardado en disco
    archivo_notif = NOTIFICATIONS_DIR / f"resumen_lote_{lote.id}_{lote.nombre_archivo}.txt"
    with open(archivo_notif, "w", encoding="utf-8") as f:
        f.write(cuerpo)

    # 2. Intento de envío SMTP si las credenciales están configuradas
    if settings.SMTP_PASSWORD and settings.SMTP_USER:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.NOTIFICACION_DESTINATARIOS
            msg["Subject"] = f"[SIAE-Vetanco] Notificación de Cierre de Lote #{lote.id} ({lote.cantidad_facturas} comprobantes)"
            msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Notificación por correo enviada con éxito.")
        except Exception as e:
            logger.warning(f"No se pudo enviar correo SMTP ({e}). Se preservó la copia en {archivo_notif}.")

    return cuerpo


def generar_lote_batch_sap(
    db: Session,
    tipo_disparo: TipoDisparoBatch = TipoDisparoBatch.MANUAL
) -> Tuple[bool, str, Optional[LoteBatch]]:
    """
    [RF-25, RF-26, RF-27]
    Compila todas las facturas listas para exportación a SAP S/4HANA:
    - Estado PROCESADA_LISTA_BATCH o APROBADA_POR_USUARIO
    - Que aún no hayan sido asignadas a un lote previo (lote_batch_id IS NULL)
    Genera el archivo CSV sin BOM en UTF-8 y actualiza el estado a CONSOLIDADA_EN_BATCH.
    """
    BATCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Facturas listas para el lote del día
    facturas_a_consolidar: List[Comprobante] = db.query(Comprobante).filter(
        Comprobante.estado.in_([
            EstadoComprobante.PROCESADA_LISTA_BATCH,
            EstadoComprobante.APROBADA_POR_USUARIO
        ]),
        Comprobante.lote_batch_id.is_(None)
    ).all()

    if not facturas_a_consolidar:
        return False, "No hay facturas listas (aprobadas o STP) pendientes de consolidar en lote", None

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"LOTE_SAP_VETANCO_{timestamp_str}.csv"
    ruta_archivo = BATCH_OUTPUT_DIR / nombre_archivo

    lineas_batch = []
    total_ars = Decimal("0.00")
    total_usd = Decimal("0.00")

    sociedad_sap = settings.SAP_SOCIEDAD

    for factura in facturas_a_consolidar:
        if factura.moneda == "USD":
            total_usd += factura.importe_total
        else:
            total_ars += factura.importe_total

        # Buscar código acreedor SAP del proveedor
        prov = db.query(Proveedor).filter(Proveedor.cuit == factura.cuit_emisor).first()
        cuenta_acreedor = prov.codigo_acreedor_sap if prov else f"PROV_{factura.cuit_emisor}"
        planta = prov.planta_default if prov else "PL01"

        fecha_doc = formatear_fecha_sap(factura.fecha_emision)
        fecha_cont = datetime.today().strftime("%Y%m%d")
        referencia = f"{factura.punto_venta:04d}-{factura.numero_comprobante:08d}"
        texto_cab = f"{factura.razon_social_emisor[:20]} OC {factura.orden_compra_nro or 'SIN OC'}"[:50]
        cae_val = factura.cae or ""
        vto_cae_val = formatear_fecha_sap(factura.vencimiento_cae)

        # -----------------------------------------------------------------
        # REGISTRO TIPO 01: Cabecera de Documento SAP (BKPF)
        # -----------------------------------------------------------------
        # 01;Clase;Sociedad;FechaDoc;FechaCont;Moneda;TipoCambio;Referencia;TextoCab;Acreedor;ImporteBruto;CAE;VtoCAE
        linea_01 = (
            f"01;KR;{sociedad_sap};{fecha_doc};{fecha_cont};{factura.moneda};"
            f"{factura.tipo_cambio:.2f};{referencia};{texto_cab};{factura.cuit_emisor};"
            f"{factura.importe_total:.2f};{cae_val};{vto_cae_val}"
        )
        lineas_batch.append(linea_01)

        # -----------------------------------------------------------------
        # REGISTRO TIPO 02: Posición de Acreedor (BSEG - Clave 31)
        # -----------------------------------------------------------------
        # 02;31;CuentaAcreedor;ImporteBruto;;;;;;;;
        linea_02_acreedor = f"02;31;{cuenta_acreedor};{factura.importe_total:.2f};;;;;;;;"
        lineas_batch.append(linea_02_acreedor)

        # -----------------------------------------------------------------
        # REGISTROS TIPO 02: Posiciones de Gasto / Materia Prima (BSEG - Clave 40)
        # -----------------------------------------------------------------
        for item in factura.items:
            cuenta_gasto = item.cuenta_contable_sugerida or "11040010"
            ind_iva = item.indicador_iva_sap or ("V2" if item.alicuota_iva == Decimal("10.50") else "V1")
            oc_nro = factura.orden_compra_nro or ""
            pos_oc = "00010"
            desc_clean = re.sub(r"[;\n\r]", " ", item.descripcion)[:50]

            linea_02_gasto = (
                f"02;40;{cuenta_gasto};{item.subtotal_linea:.2f};{ind_iva};{planta};"
                f"{oc_nro};{pos_oc};{item.cantidad:.1f};{item.unidad_medida};{desc_clean}"
            )
            lineas_batch.append(linea_02_gasto)

            # Descontar del saldo remanente de la OC si existe en Staging
            if oc_nro and item.codigo_insumo:
                oc_item = db.query(OrdenCompraItem).filter(
                    OrdenCompraItem.numero_oc == oc_nro,
                    OrdenCompraItem.codigo_insumo == item.codigo_insumo
                ).first()
                if oc_item:
                    nuevo_remanente = max(0.0, oc_item.cantidad_remanente - item.cantidad)
                    oc_item.cantidad_remanente = nuevo_remanente

        # Posición de Percepción IIBB si existe
        if factura.percepcion_iibb and factura.percepcion_iibb > Decimal("0.00"):
            juris = factura.percepcion_iibb_jurisdiccion or "Bs As"
            linea_iibb = f"02;40;11080020;{factura.percepcion_iibb:.2f};IB;{planta};;;;Percepcion IIBB {juris}"
            lineas_batch.append(linea_iibb)

    # Escritura estricta UTF-8 sin BOM (delimitado por ;)
    contenido_csv = "\r\n".join(lineas_batch) + "\r\n"
    csv_bytes = contenido_csv.encode("utf-8")  # Sin BOM

    with open(ruta_archivo, "wb") as f:
        f.write(csv_bytes)

    # Hash SHA-256 del archivo
    hasher = hashlib.sha256()
    hasher.update(csv_bytes)
    sha256_archivo = hasher.hexdigest()

    # Contar comprobantes pendientes de auditoría
    pendientes_count = db.query(Comprobante).filter(
        Comprobante.estado == EstadoComprobante.REQUIERE_AUDITORIA
    ).count()

    # Registrar LoteBatch en la BD
    lote = LoteBatch(
        nombre_archivo=nombre_archivo,
        ruta_archivo=str(ruta_archivo),
        fecha_generacion=datetime.now(),
        tipo_disparo=tipo_disparo,
        cantidad_facturas=len(facturas_a_consolidar),
        total_ars=total_ars,
        total_usd=total_usd,
        sha256_hash=sha256_archivo
    )
    db.add(lote)
    db.flush()

    # Actualizar estado de las facturas consolidadas
    for factura in facturas_a_consolidar:
        factura.estado = EstadoComprobante.CONSOLIDADA_EN_BATCH
        factura.lote_batch_id = lote.id

    resumen_texto = enviar_notificacion_cierre_lote(lote, pendientes_count)
    lote.resumen_notificacion = resumen_texto

    db.commit()
    db.refresh(lote)

    return True, f"Lote #{lote.id} generado exitosamente con {len(facturas_a_consolidar)} comprobantes", lote
