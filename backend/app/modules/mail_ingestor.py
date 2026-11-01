"""
Módulo 1: Ingestor de Correos y Recepción de Archivos (Worker Background)
[RF-01 a RF-05]
Soporta:
1. Conexión segura IMAP/TLS puerto 993 con App Password o XOAUTH2 (Gmail).
2. Bandeja de entrada local simulada (data/casilla_entrante/) para pruebas sin conexión.
3. Carga directa de comprobantes desde la interfaz web.
4. Filtro inteligente anti-spam, prevención de duplicados (Message-ID), hash SHA-256
   y orquestación automática con el extractor y el motor de reglas.
"""
import email
from email import policy
import hashlib
import imaplib
import logging
import os
import re
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings, PDF_STORAGE_DIR, INBOX_DROP_DIR
from app.models import Comprobante, ComprobanteItem, EstadoComprobante, Proveedor
import pymupdf as fitz
from app.modules.gemini_extractor import extraer_datos_factura
from app.modules.validators import (
    evaluar_comprobante_integral,
    comprobar_duplicado_fiscal,
    limpiar_cuit,
    a_decimal
)

logger = logging.getLogger("siae.ingestor")

# Palabras clave fiscales requeridas para filtrar spam o adjuntos no válidos (RF-03)
KEYWORDS_FISCALES = [
    "FACTURA", "COMPROBANTE", "CUIT", "PUNTO DE VENTA", "CAE", "ARCA", "AFIP", "IVA",
    "NOTA DE CREDITO", "NOTA DE DEBITO", "ORDEN DE COMPRA", "ORIGINAL", "DUPLICADO"
]


def calcular_sha256(data_bytes: bytes) -> str:
    """[RF-04] Calcula el hash criptográfico SHA-256 de los bytes del archivo PDF."""
    hasher = hashlib.sha256()
    hasher.update(data_bytes)
    return hasher.hexdigest()


def es_archivo_factura_valido(filename: str, pdf_bytes: bytes) -> Tuple[bool, str]:
    """
    [RF-03] Filtro inteligente de comprobantes:
    1. Verifica extensión .pdf y cabecera mágica '%PDF-'.
    2. Escaneo superficial de keywords fiscales para descartar presupuestos o spam.
    """
    if not filename.lower().endswith(".pdf"):
        return False, f"Archivo descartado: extensión no soportada ({filename})"

    # Permitir cabeceras con caracteres iniciales menores a 1024 bytes (ej: generadores TCPDF con ';%PDF-')
    pos_pdf = pdf_bytes[:1024].find(b"%PDF-")
    if pos_pdf == -1:
        return False, "Archivo descartado: cabecera corrupta o no es un PDF nativo"
    if pos_pdf > 0:
        pdf_bytes = pdf_bytes[pos_pdf:]

    # Escaneo superficial de texto usando PyMuPDF sobre el stream en memoria
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            doc.close()
            return False, "Archivo descartado: el documento PDF no contiene páginas"
        texto_primera_pag = doc[0].get_text("text").upper()
        num_imagenes = len(doc[0].get_images())
        doc.close()

        # Si el PDF posee capa de texto digital, validar términos fiscales mínimos (RF-03)
        if len(texto_primera_pag.strip()) > 30:
            coincidencias = sum(1 for kw in KEYWORDS_FISCALES if kw in texto_primera_pag)
            if coincidencias == 0:
                return False, "Filtro anti-spam: comprobante sin términos fiscales AFIP/ARCA mínimos"
        elif num_imagenes > 0:
            # Comprobante escaneado o rasterizado (ej: impresión como imagen de Outlook)
            logger.info(f"Comprobante '{filename}' identificado como documento escaneado/rasterizado ({num_imagenes} imágenes). Habilitado para análisis multimodal.")
        else:
            return False, "Archivo descartado: el documento está en blanco (sin texto ni imágenes)"
    except Exception as e:
        return False, f"Archivo descartado: error al abrir PDF ({e})"

    return True, "Comprobante formalmente válido para procesamiento"


def procesar_comprobante_pdf(
    db: Session,
    pdf_bytes: bytes,
    nombre_archivo_original: str,
    message_id: Optional[str] = None,
    remitente: Optional[str] = None,
    asunto: Optional[str] = None
) -> Tuple[bool, str, Optional[Comprobante]]:
    """
    Flujo central de ingesta:
    1. Filtro anti-spam (RF-03)
    2. Prevención de Message-ID duplicado (RF-05)
    3. Hashing SHA-256 y guardado seguro en data/pdfs/{uuid4}.pdf (RF-04)
    4. Extracción de datos (Módulo 2 Gemini / Fallback)
    5. Validación contable y conciliación OC (Módulo 3)
    6. Persistencia en SQLite Staging
    """
    # 1. Filtro anti-spam
    valido, razon_filtro = es_archivo_factura_valido(nombre_archivo_original, pdf_bytes)
    if not valido:
        logger.warning(f"Descarte anti-spam para '{nombre_archivo_original}': {razon_filtro}")
        return False, razon_filtro, None

    # Normalizar bytes si poseía cabecera desplazada (ej: TCPDF con ';')
    pos_pdf = pdf_bytes[:1024].find(b"%PDF-")
    if pos_pdf > 0:
        pdf_bytes = pdf_bytes[pos_pdf:]

    # 2. Control de Message-ID duplicado en BD (RF-05)
    if message_id:
        existente = db.query(Comprobante).filter(Comprobante.message_id == message_id).first()
        if existente:
            msg = f"Correo duplicado ignorado: Message-ID {message_id} ya fue procesado previamente"
            logger.info(msg)
            return False, msg, existente

    # 3. Hash SHA-256 y prevención de archivo duplicado (RF-04)
    sha256 = calcular_sha256(pdf_bytes)
    existente_sha = db.query(Comprobante).filter(Comprobante.sha256_hash == sha256).first()
    if existente_sha:
        estado_val = existente_sha.estado.value if hasattr(existente_sha.estado, "value") else str(existente_sha.estado)
        msg = (
            f"El archivo PDF ya fue ingresado previamente al sistema. "
            f"Corresponde a la factura {existente_sha.letra} {existente_sha.punto_venta:04d}-{existente_sha.numero_comprobante:08d} "
            f"de '{existente_sha.razon_social_emisor}' (CUIT: {existente_sha.cuit_emisor}), "
            f"en estado actual: '{estado_val}' (ID: {existente_sha.id[:8]})."
        )
        logger.warning(msg)
        return False, msg, existente_sha

    nuevo_id = str(uuid.uuid4())
    nombre_guardado = f"{nuevo_id}.pdf"
    ruta_guardado = PDF_STORAGE_DIR / nombre_guardado

    with open(ruta_guardado, "wb") as f:
        f.write(pdf_bytes)

    # 4. Extracción de datos
    try:
        extraccion = extraer_datos_factura(str(ruta_guardado))
    except Exception as e:
        logger.error(f"Error procesando PDF con extractor: {e}")
        # En caso de error crítico de parseo, se almacena como REQUIERE_AUDITORIA
        comprobante = Comprobante(
            id=nuevo_id,
            message_id=message_id,
            archivo_pdf_path=str(ruta_guardado),
            sha256_hash=sha256,
            cuit_emisor="00000000000",
            razon_social_emisor="EMISOR DESCONOCIDO",
            tipo_comprobante="001",
            letra="A",
            punto_venta=1,
            numero_comprobante=1,
            fecha_emision=date.today(),
            importe_total=a_decimal(0),
            confianza_global=0.0,
            confianza_campos={},
            alertas_validacion=[{"codigo": "ERROR_PARSEO_PDF", "campo": "archivo", "mensaje": str(e), "severidad": "error"}],
            estado=EstadoComprobante.REQUIERE_AUDITORIA
        )
        db.add(comprobante)
        db.commit()
        db.refresh(comprobante)
        return True, "Comprobante guardado con requerimiento de auditoría por error de lectura", comprobante

    cab_dict = extraccion.comprobante.model_dump()
    sub_dict = extraccion.subtotales.model_dump()
    items_list = [it.model_dump() for it in extraccion.items]

    # Control de duplicado fiscal estricto (RF-17) antes de persistir
    cuit_emisor_limpio = limpiar_cuit(cab_dict.get("cuit_emisor"))
    tipo_comp_str = str(cab_dict.get("tipo_comprobante", "001")).zfill(3)
    pv_int = int(cab_dict.get("punto_venta", 1))
    nro_int = int(cab_dict.get("numero_comprobante", 1))

    es_dup, msg_dup = comprobar_duplicado_fiscal(
        db=db,
        cuit_emisor=cuit_emisor_limpio,
        tipo_comprobante=tipo_comp_str,
        punto_venta=pv_int,
        numero_comprobante=nro_int
    )
    if es_dup:
        if ruta_guardado.exists():
            ruta_guardado.unlink(missing_ok=True)
        logger.warning(f"Comprobante fiscal duplicado descartado: {msg_dup}")
        return False, msg_dup, None

    # 5. Evaluación de Reglas de Negocio (Módulo 3)

    evaluacion = evaluar_comprobante_integral(
        db=db,
        cabecera=cab_dict,
        subtotales=sub_dict,
        items=items_list,
        confianza_global=extraccion.meta.confianza_promedio,
        confianza_campos=extraccion.meta.confianza_campos
    )

    # Parsing seguro de fechas
    def parse_fecha(f_str: Optional[str]) -> Optional[date]:
        if not f_str:
            return None
        try:
            return datetime.strptime(f_str.strip(), "%Y-%m-%d").date()
        except Exception:
            return None

    fecha_emision = parse_fecha(cab_dict.get("fecha_emision")) or date.today()
    fecha_vto = parse_fecha(cab_dict.get("fecha_vencimiento"))
    vto_cae = parse_fecha(cab_dict.get("vencimiento_cae"))

    # Crear entidad Comprobante en Staging
    comprobante = Comprobante(
        id=nuevo_id,
        message_id=message_id,
        archivo_pdf_path=str(ruta_guardado),
        sha256_hash=sha256,
        cuit_emisor=limpiar_cuit(cab_dict.get("cuit_emisor")),
        razon_social_emisor=cab_dict.get("razon_social_emisor") or "PROVEEDOR S.A.",
        tipo_comprobante=str(cab_dict.get("tipo_comprobante", "001")).zfill(3),
        letra=cab_dict.get("letra", "A"),
        punto_venta=int(cab_dict.get("punto_venta", 1)),
        numero_comprobante=int(cab_dict.get("numero_comprobante", 1)),
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vto,
        cae=cab_dict.get("cae"),
        vencimiento_cae=vto_cae,
        cuit_receptor=cab_dict.get("cuit_receptor") or settings.VETANCO_CUIT,
        moneda=sub_dict.get("moneda", "ARS"),
        tipo_cambio=a_decimal(sub_dict.get("tipo_cambio", 1.0)),
        neto_gravado_21=a_decimal(sub_dict.get("neto_gravado_21")),
        neto_gravado_105=a_decimal(sub_dict.get("neto_gravado_105")),
        neto_gravado_27=a_decimal(sub_dict.get("neto_gravado_27")),
        no_gravado=a_decimal(sub_dict.get("no_gravado")),
        exento=a_decimal(sub_dict.get("exento")),
        iva_21=a_decimal(sub_dict.get("iva_21")),
        iva_105=a_decimal(sub_dict.get("iva_105")),
        iva_27=a_decimal(sub_dict.get("iva_27")),
        percepcion_iibb=a_decimal(sub_dict.get("percepcion_iibb")),
        percepcion_iibb_jurisdiccion=sub_dict.get("percepcion_iibb_jurisdiccion"),
        percepcion_iva=a_decimal(sub_dict.get("percepcion_iva")),
        impuestos_internos=a_decimal(sub_dict.get("impuestos_internos")),
        importe_total=a_decimal(sub_dict.get("total")),
        orden_compra_nro=cab_dict.get("orden_compra"),
        confianza_global=extraccion.meta.confianza_promedio,
        confianza_campos=extraccion.meta.confianza_campos,
        alertas_validacion=evaluacion["alertas"],
        estado=evaluacion["estado"],
        motivo_rechazo=evaluacion["motivo_rechazo"]
    )

    db.add(comprobante)
    db.flush()

    # Guardar ítems asociados
    for it in items_list:
        item_obj = ComprobanteItem(
            comprobante_id=nuevo_id,
            posicion=it.get("posicion", 1),
            codigo_insumo=it.get("codigo_insumo"),
            descripcion=it.get("descripcion", "Materia Prima"),
            cantidad=float(it.get("cantidad", 1.0)),
            unidad_medida=it.get("unidad_medida", "KG"),
            precio_unitario=a_decimal(it.get("precio_unitario")),
            subtotal_linea=a_decimal(it.get("subtotal")),
            alicuota_iva=a_decimal(it.get("alicuota_iva", 21.0)),
            cuenta_contable_sugerida="11040010",
            indicador_iva_sap="V1"
        )
        db.add(item_obj)

    db.commit()
    db.refresh(comprobante)
    return True, f"Comprobante registrado con éxito. Estado: {comprobante.estado.value}", comprobante


def sincronizar_bandeja_local(db: Session) -> Dict[str, Any]:
    """
    [Simulador de Casilla Local]
    Escanea la carpeta data/casilla_entrante/ buscando archivos .pdf o .eml
    que hayan sido depositados manualmente para simular recepción de mails.
    """
    INBOX_DROP_DIR.mkdir(parents=True, exist_ok=True)
    archivos = list(INBOX_DROP_DIR.glob("*.pdf"))
    procesados = 0
    descartados = 0
    errores = []

    for archivo in archivos:
        try:
            with open(archivo, "rb") as f:
                pdf_bytes = f.read()

            nombre = archivo.name
            simulated_msg_id = f"LOCAL_{archivo.stem}_{len(pdf_bytes)}"

            ok, mensaje, comp = procesar_comprobante_pdf(
                db=db,
                pdf_bytes=pdf_bytes,
                nombre_archivo_original=nombre,
                message_id=simulated_msg_id,
                remitente="proveedor.simulado@vetanco-test.com",
                asunto=f"Factura de prueba {archivo.stem}"
            )
            if ok:
                procesados += 1
                # Mover a carpeta de procesados para no reescanearlo
                procesados_dir = INBOX_DROP_DIR / "procesados"
                procesados_dir.mkdir(exist_ok=True)
                archivo.rename(procesados_dir / archivo.name)
            else:
                descartados += 1
                errores.append(f"{nombre}: {mensaje}")
        except Exception as e:
            logger.error(f"Error procesando archivo local '{archivo.name}': {e}")
            descartados += 1
            errores.append(f"{archivo.name}: {str(e)}")

    return {
        "origen": "bandeja_local",
        "total_encontrados": len(archivos),
        "procesados": procesados,
        "descartados": descartados,
        "errores": errores
    }


def sincronizar_casilla_imap(db: Session) -> Dict[str, Any]:
    """
    [RF-01, RF-02] Conexión formal IMAP4_SSL sobre puerto 993 con facturas.proveedores.test.franco@gmail.com.
    Descarga correos no leídos (UNSEEN), extrae adjuntos PDF y aplica el flujo integral.
    """
    if not settings.IMAP_USER or not settings.IMAP_PASSWORD:
        logger.info("Credenciales IMAP no configuradas en .env. Usando sincronización local de respaldo.")
        return sincronizar_bandeja_local(db)

    procesados = 0
    descartados = 0
    errores = []

    try:
        logger.info(f"Conectando por IMAP/TLS a {settings.IMAP_HOST}:{settings.IMAP_PORT} con usuario {settings.IMAP_USER}...")
        mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        mail.select("INBOX")

        # Buscar correos no leídos
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            mail.close()
            mail.logout()
            return {"origen": "imap_gmail", "procesados": 0, "mensajes": "No hay correos UNSEEN"}

        mail_ids = data[0].split()
        logger.info(f"Se encontraron {len(mail_ids)} correos pendientes en la casilla.")

        for num in mail_ids:
            res, msg_data = mail.fetch(num, "(RFC822)")
            if res != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email, policy=policy.default)

            message_id = msg.get("Message-ID", f"IMAP_{num.decode()}")
            remitente = msg.get("From", "")
            asunto = msg.get("Subject", "")

            adjuntos_encontrados = 0

            # Iterar partes buscando PDFs
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                filename = part.get_filename()
                if not filename:
                    continue

                if filename.lower().endswith(".pdf"):
                    adjuntos_encontrados += 1
                    pdf_bytes = part.get_payload(decode=True)

                    ok, motivo, comp = procesar_comprobante_pdf(
                        db=db,
                        pdf_bytes=pdf_bytes,
                        nombre_archivo_original=filename,
                        message_id=f"{message_id}_{adjuntos_encontrados}",
                        remitente=remitente,
                        asunto=asunto
                    )
                    if ok:
                        procesados += 1
                    else:
                        descartados += 1
                        errores.append(f"{filename}: {motivo}")

            if adjuntos_encontrados == 0:
                descartados += 1
                errores.append(f"Correo {asunto}: sin archivos adjuntos PDF")

        mail.close()
        mail.logout()

    except Exception as e:
        logger.error(f"Error conectando a servidor IMAP: {e}")
        # En caso de fallo de red en clase, fallback automático a bandeja local
        fallback_res = sincronizar_bandeja_local(db)
        fallback_res["error_imap_original"] = str(e)
        return fallback_res

    return {
        "origen": "imap_gmail",
        "procesados": procesados,
        "descartados": descartados,
        "errores": errores
    }


def ejecutar_ingesta_automatica(db: Session) -> Dict[str, Any]:
    """Punto de entrada general para el worker programado y la API."""
    if settings.MAIL_INGESTION_MODE == "imap" and settings.IMAP_PASSWORD:
        return sincronizar_casilla_imap(db)
    else:
        return sincronizar_bandeja_local(db)
