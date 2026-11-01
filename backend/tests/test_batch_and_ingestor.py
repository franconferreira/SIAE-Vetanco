import os
import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path
import pymupdf as fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Comprobante,
    ComprobanteItem,
    EstadoComprobante,
    Proveedor,
    OrdenCompra,
    OrdenCompraItem,
    TipoDisparoBatch
)
from app.modules.mail_ingestor import (
    es_archivo_factura_valido,
    calcular_sha256,
    procesar_comprobante_pdf
)
from app.modules.batch_exporter import generar_lote_batch_sap
from app.modules.scheduler import scheduler, iniciar_scheduler, detener_scheduler


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_batch.db")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    # Proveedor de prueba
    prov = Proveedor(
        cuit="30708912014",
        razon_social="QUIMICA VETERINARIA ARGENTINA S.A.",
        codigo_acreedor_sap="PROV_30708912014",
        planta_default="PL01"
    )
    db.add(prov)

    # Orden de Compra de prueba
    oc = OrdenCompra(
        numero_oc="4500098124",
        cuit_proveedor="30708912014",
        estado="ABIERTA",
        moneda="ARS"
    )
    db.add(oc)

    # Ítem de OC con remanente inicial 100.0
    item_oc = OrdenCompraItem(
        numero_oc="4500098124",
        posicion_sap="00010",
        codigo_insumo="MP-VET-001",
        descripcion="Principio Activo Ivermectina 99%",
        cantidad_pedida=100.0,
        cantidad_remanente=100.0,
        unidad_medida="KG",
        precio_unitario=Decimal("3000.00"),
        cuenta_contable_sap="11040010"
    )
    db.add(item_oc)
    db.commit()

    try:
        yield db
    finally:
        db.close()


def crear_pdf_valido_bytes():
    """Genera en memoria un PDF digital con términos fiscales válidos."""
    doc = fitz.open()
    page = doc.new_page()
    texto = (
        "FACTURA A\n"
        "COD. 001\n"
        "QUIMICA VETERINARIA ARGENTINA S.A.\n"
        "CUIT: 30-70891201-4\n"
        "Punto de Venta: 0004 Comp. Nro: 00012845\n"
        "Fecha de Emisión: 14/10/2026\n"
        "CLIENTE: VETANCO S.A.\n"
        "CUIT: 30-62336893-9\n"
        "Orden de Compra: 4500098124\n"
        "50.0 KG Principio Activo Ivermectina 3000.00 150000.00\n"
        "Subtotal Neto Gravado: $ 150.000,00\n"
        "IVA 21%: $ 31.500,00\n"
        "Importe Total: $ 181.500,00\n"
        "CAE: 74418901234567\n"
        "Fecha de Vto. de CAE: 24/10/2026\n"
    )
    page.insert_text((50, 70), texto, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_filtro_antispam_rf03():
    # 1. Archivo no PDF
    ok, msg = es_archivo_factura_valido("presupuesto.docx", b"texto")
    assert ok is False

    # 2. PDF que no es válido
    ok, msg = es_archivo_factura_valido("factura.pdf", b"archivo corrupto")
    assert ok is False

    # 3. PDF sin términos fiscales
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hola mundo, esto es una receta de cocina sin datos fiscales.")
    pdf_spam = doc.tobytes()
    doc.close()

    ok, msg = es_archivo_factura_valido("carta.pdf", pdf_spam)
    assert ok is False
    assert "Filtro anti-spam" in msg

    # 4. PDF fiscal válido
    pdf_valido = crear_pdf_valido_bytes()
    ok_valido, _ = es_archivo_factura_valido("factura_quimica.pdf", pdf_valido)
    assert ok_valido is True


def test_ingesta_y_deduplicacion_rf04_rf05(db_session):
    pdf_bytes = crear_pdf_valido_bytes()
    msg_id = "TEST_MSG_ID_12345"

    # Ingesta 1: debe registrar el comprobante
    ok1, msg1, comp1 = procesar_comprobante_pdf(
        db=db_session,
        pdf_bytes=pdf_bytes,
        nombre_archivo_original="factura_quimica.pdf",
        message_id=msg_id,
        remitente="proveedor@quimica.com",
        asunto="Factura Quimica 12845"
    )
    assert ok1 is True
    assert comp1 is not None
    assert comp1.sha256_hash == calcular_sha256(pdf_bytes)
    assert comp1.message_id == msg_id

    # Ingesta 2: mismo Message-ID -> debe descartar por duplicado de correo (RF-05)
    ok2, msg2, comp2 = procesar_comprobante_pdf(
        db=db_session,
        pdf_bytes=pdf_bytes,
        nombre_archivo_original="factura_quimica.pdf",
        message_id=msg_id
    )
    assert ok2 is False
    assert "Message-ID" in msg2


def test_exportador_batch_sap_rf27_rf28(db_session):
    # Sin facturas aprobadas -> debe informar que no hay facturas
    ok_vacio, msg_vacio, _ = generar_lote_batch_sap(db_session)
    assert ok_vacio is False

    # Insertar un comprobante en PROCESADA_LISTA_BATCH
    pdf_bytes = crear_pdf_valido_bytes()
    sha = calcular_sha256(pdf_bytes)

    comp = Comprobante(
        id="comp-test-batch-001",
        archivo_pdf_path="dummy.pdf",
        sha256_hash=sha,
        cuit_emisor="30708912014",
        razon_social_emisor="QUIMICA VETERINARIA ARGENTINA S.A.",
        tipo_comprobante="001",
        letra="A",
        punto_venta=4,
        numero_comprobante=12845,
        fecha_emision=date(2026, 10, 14),
        fecha_vencimiento=date(2026, 10, 24),
        cae="74418901234567",
        vencimiento_cae=date(2026, 10, 24),
        moneda="ARS",
        tipo_cambio=Decimal("1.00"),
        neto_gravado_21=Decimal("150000.00"),
        iva_21=Decimal("31500.00"),
        percepcion_iibb=Decimal("5250.00"),
        percepcion_iibb_jurisdiccion="Buenos Aires",
        importe_total=Decimal("186750.00"),
        orden_compra_nro="4500098124",
        confianza_global=0.98,
        estado=EstadoComprobante.PROCESADA_LISTA_BATCH
    )
    db_session.add(comp)
    db_session.flush()

    item = ComprobanteItem(
        comprobante_id=comp.id,
        posicion=1,
        codigo_insumo="MP-VET-001",
        descripcion="Principio Activo Ivermectina 99%",
        cantidad=50.0,
        unidad_medida="KG",
        precio_unitario=Decimal("3000.00"),
        subtotal_linea=Decimal("150000.00"),
        alicuota_iva=Decimal("21.00"),
        cuenta_contable_sugerida="11040010",
        indicador_iva_sap="V1"
    )
    db_session.add(item)
    db_session.commit()

    # Generar el Lote Batch
    ok_lote, msg_lote, lote = generar_lote_batch_sap(db_session, TipoDisparoBatch.MANUAL)
    assert ok_lote is True
    assert lote is not None
    assert lote.cantidad_facturas == 1
    assert lote.total_ars == Decimal("186750.00")

    # 1. Verificar archivo físico generado
    ruta_archivo = Path(lote.ruta_archivo)
    assert ruta_archivo.exists()

    contenido_bytes = ruta_archivo.read_bytes()
    # Verificar que NO tenga BOM UTF-8 (no debe empezar con \xef\xbb\xbf)
    assert not contenido_bytes.startswith(b"\xef\xbb\xbf")

    contenido_texto = contenido_bytes.decode("utf-8")
    lineas = [l for l in contenido_texto.strip().split("\r\n") if l]

    # Verificar Registro Tipo 01 (BKPF)
    assert lineas[0].startswith("01;KR;AR01;")
    assert "0004-00012845" in lineas[0]
    assert "30708912014" in lineas[0]
    assert "186750.00" in lineas[0]
    assert "74418901234567" in lineas[0]

    # Verificar Registro Tipo 02 Acreedor (BSEG 31)
    assert lineas[1].startswith("02;31;PROV_30708912014;186750.00")

    # Verificar Registro Tipo 02 Gasto/Materia Prima (BSEG 40)
    assert lineas[2].startswith("02;40;11040010;150000.00;V1;PL01;4500098124;00010;50.0;KG;")

    # Verificar Registro Tipo 02 Percepción IIBB
    assert lineas[3].startswith("02;40;11080020;5250.00;IB;PL01;;;;Percepcion IIBB")

    # 2. Verificar transición de estado del comprobante a CONSOLIDADA_EN_BATCH
    db_session.refresh(comp)
    assert comp.estado == EstadoComprobante.CONSOLIDADA_EN_BATCH
    assert comp.lote_batch_id == lote.id

    # 3. Verificar que se descontó la cantidad de la OC remanente (100 - 50 = 50)
    oc_item = db_session.query(OrdenCompraItem).filter_by(codigo_insumo="MP-VET-001").first()
    assert oc_item.cantidad_remanente == 50.0


def test_scheduler_lifecycle():
    # Verificar arranque y parada limpia del scheduler
    iniciar_scheduler()
    assert scheduler.running is True
    assert scheduler.get_job("job_escanear_correos") is not None
    assert scheduler.get_job("job_cierre_batch_diario") is not None

    detener_scheduler()
    assert scheduler.running is False
