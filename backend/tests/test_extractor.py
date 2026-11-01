import pytest
from pathlib import Path
import pymupdf as fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.modules.supplier_templates import (
    PROVEEDORES_RECURRENTES,
    sembrar_proveedores_en_bd,
    buscar_plantilla_por_cuit_o_texto
)
from app.modules.gemini_extractor import extraer_datos_factura
from app.schemas import FacturaExtraidaSchema


def test_catalogo_20_proveedores():
    # RF-07: Catálogo de 20 proveedores recurrentes
    assert len(PROVEEDORES_RECURRENTES) == 20

    # Verificar estructura mínima
    for prov in PROVEEDORES_RECURRENTES:
        assert len(prov["cuit"]) == 11
        assert "PROV_" in prov["codigo_acreedor_sap"]
        assert prov["planta_default"] in ("PL01", "PL02")
        assert len(prov["few_shot_hint"]) > 20


def test_sembrar_proveedores_en_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    insertados = sembrar_proveedores_en_bd(db)
    assert insertados == 20

    # Si se vuelve a sembrar, no debe duplicar registros
    reinsertados = sembrar_proveedores_en_bd(db)
    assert reinsertados == 0
    db.close()


def test_extraccion_directa_pdf_fallback(tmp_path):
    # Generar un PDF digital nativo con PyMuPDF simulando factura AFIP
    pdf_file = tmp_path / "factura_test_afip.pdf"
    doc = fitz.open()
    page = doc.new_page()

    texto_factura = (
        "FACTURA A\n"
        "COD. 001\n"
        "QUIMICA VETERINARIA ARGENTINA S.A.\n"
        "CUIT: 30-70891201-4\n"
        "Punto de Venta: 0004 Comp. Nro: 00012845\n"
        "Fecha de Emisión: 14/10/2026\n\n"
        "CLIENTE: VETANCO S.A.\n"
        "CUIT: 30-62336893-9\n"
        "Condición IVA: IVA Responsable Inscripto\n"
        "Orden de Compra: 4500098124\n\n"
        "DETALLE:\n"
        "50.0 KG Principio Activo Ivermectina 99% 3000.00 150000.00\n\n"
        "Subtotal Neto Gravado: $ 150.000,00\n"
        "IVA 21%: $ 31.500,00\n"
        "Percepción IIBB: $ 0,00\n"
        "Importe Total: $ 181.500,00\n\n"
        "CAE: 74418901234567\n"
        "Fecha de Vto. de CAE: 24/10/2026\n"
    )

    page.insert_text((50, 70), texto_factura, fontsize=11)
    doc.save(str(pdf_file))
    doc.close()

    # Ejecutar extracción directa
    resultado = extraer_datos_factura(str(pdf_file))

    assert isinstance(resultado, FacturaExtraidaSchema)
    assert resultado.comprobante.cuit_emisor == "30708912014"
    assert resultado.comprobante.cuit_receptor == "30623368939"
    assert resultado.comprobante.tipo_comprobante == "001"
    assert resultado.comprobante.punto_venta == 4
    assert resultado.comprobante.numero_comprobante == 12845
    assert resultado.comprobante.cae == "74418901234567"
    assert resultado.comprobante.orden_compra == "4500098124"
    assert resultado.subtotales.neto_gravado_21 == 150000.0
    assert resultado.subtotales.iva_21 == 31500.0
    assert resultado.subtotales.total == 181500.0
    assert resultado.meta.confianza_promedio >= 0.90
    assert len(resultado.items) >= 1
