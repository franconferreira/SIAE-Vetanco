import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Proveedor, OrdenCompra, OrdenCompraItem, Comprobante, EstadoComprobante
from app.modules.validators import (
    validar_cuit_afip_modulo11,
    validar_receptor_vetanco,
    validar_consistencia_impositiva,
    conciliar_orden_compra,
    evaluar_comprobante_integral,
    comprobar_duplicado_fiscal
)


@pytest.fixture
def db_session():
    """Sesión SQLite en memoria para tests aislados y rápidos."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Cargar Proveedor de prueba
    prov = Proveedor(
        cuit="30708912345",  # CUIT emisor de prueba
        razon_social="QUIMICA VETERINARIA ARGENTINA S.A.",
        codigo_acreedor_sap="PROV_30708912345",
        planta_default="PL01"
    )
    db.add(prov)

    # Cargar Orden de Compra abierta
    oc = OrdenCompra(
        numero_oc="4500098124",
        cuit_proveedor="30708912345",
        estado="ABIERTA",
        moneda="ARS"
    )
    db.add(oc)

    # Ítem de la OC
    oc_item = OrdenCompraItem(
        numero_oc="4500098124",
        posicion_sap="00010",
        codigo_insumo="MP-VET-098",
        descripcion="Principio Activo Ivermectina 99% USP",
        cantidad_pedida=100.0,
        cantidad_remanente=50.0,
        unidad_medida="KG",
        precio_unitario=Decimal("3000.00"),
        cuenta_contable_sap="11040010"
    )
    db.add(oc_item)
    db.commit()

    try:
        yield db
    finally:
        db.close()


def test_rf15_modulo11_cuit():
    # CUIT institucional Vetanco S.A.
    valido_vetanco, _ = validar_cuit_afip_modulo11("30-62336893-9")
    assert valido_vetanco is True

    # CUIT proveedor real con Módulo 11 exacto (30-70891234-0)
    valido_prov, msg = validar_cuit_afip_modulo11("30-70891234-0")
    assert valido_prov is True

    # CUIT con dígito verificador erróneo (debería ser 0, le ponemos 7)
    invalido, msg = validar_cuit_afip_modulo11("30-70891234-7")
    assert invalido is False
    assert "dígito verificador no coincide" in msg

    # Longitud incorrecta
    invalido_len, _ = validar_cuit_afip_modulo11("12345")
    assert invalido_len is False


def test_rf14_receptor_vetanco():
    # Receptor correcto
    valido, _ = validar_receptor_vetanco("30-62336893-9")
    assert valido is True

    # Factura enviada a otra empresa
    invalido, msg = validar_receptor_vetanco("30-99999999-9")
    assert invalido is False
    assert "no pertenece a Vetanco S.A." in msg


def test_rf13_consistencia_impositiva():
    # Caso exacto: Neto 150000 + IVA 31500 + IIBB 5250 = Total 186750
    datos = {
        "neto_gravado_21": 150000.00,
        "iva_21": 31500.00,
        "percepcion_iibb": 5250.00,
        "total": 186750.00
    }
    ok, calc, inf, alertas = validar_consistencia_impositiva(datos)
    assert ok is True
    assert calc == Decimal("186750.00")
    assert inf == Decimal("186750.00")
    assert len(alertas) == 0

    # Caso dentro de tolerancia (+ $0.02)
    datos_tolerancia = {
        "neto_gravado_21": 150000.00,
        "iva_21": 31500.00,
        "total": 181500.02
    }
    ok_tol, _, _, alertas_tol = validar_consistencia_impositiva(datos_tolerancia)
    assert ok_tol is True

    # Caso discrepancia fuera de tolerancia (+ $10.00)
    datos_discrepancia = {
        "neto_gravado_21": 150000.00,
        "iva_21": 31500.00,
        "total": 181510.00
    }
    ok_disc, calc_disc, inf_disc, alertas_disc = validar_consistencia_impositiva(datos_discrepancia)
    assert ok_disc is False
    assert any(a["codigo"] == "DISCREPANCIA_SUMA_IMPOSITIVA" for a in alertas_disc)


def test_rf16_conciliacion_orden_compra(db_session):
    # Caso correcto: coincide precio y cantidad
    items_ok = [{
        "codigo_insumo": "MP-VET-098",
        "descripcion": "Principio Activo Ivermectina",
        "cantidad": 50.0,
        "precio_unitario": Decimal("3000.00")
    }]
    ok, oc, alertas = conciliar_orden_compra(db_session, "4500098124", "30708912345", items_ok)
    assert ok is True
    assert len(alertas) == 0

    # Caso sobreprecio: factura a $3500 cuando en OC está a $3000
    items_sobreprecio = [{
        "codigo_insumo": "MP-VET-098",
        "descripcion": "Principio Activo Ivermectina",
        "cantidad": 50.0,
        "precio_unitario": Decimal("3500.00")
    }]
    ok_sp, _, alertas_sp = conciliar_orden_compra(db_session, "4500098124", "30708912345", items_sobreprecio)
    assert ok_sp is False
    assert any(a["codigo"] == "PRECIO_EXCEDE_OC" for a in alertas_sp)

    # Caso cantidad excede remanente: remanente es 50, factura 80
    items_exceso_cant = [{
        "codigo_insumo": "MP-VET-098",
        "descripcion": "Principio Activo Ivermectina",
        "cantidad": 80.0,
        "precio_unitario": Decimal("3000.00")
    }]
    ok_cant, _, alertas_cant = conciliar_orden_compra(db_session, "4500098124", "30708912345", items_exceso_cant)
    assert any(a["codigo"] == "CANTIDAD_SUPERA_SALDO_OC" for a in alertas_cant)


def test_rf18_maquina_estados_integral(db_session):
    cabecera_ok = {
        "cuit_emisor": "30623368939",  # CUIT válido
        "tipo_comprobante": "001",
        "punto_venta": 4,
        "numero_comprobante": 12845,
        "cuit_receptor": "30623368939",
        "orden_compra": "4500098124",
        "cae": "74418901234567"
    }
    # Cargar proveedor con este CUIT para el test
    db_session.add(Proveedor(
        cuit="30623368939",
        razon_social="PROVEEDOR TEST",
        codigo_acreedor_sap="PROV_30623368939"
    ))
    # Actualizar proveedor de la OC
    oc = db_session.query(OrdenCompra).filter_by(numero_oc="4500098124").first()
    oc.cuit_proveedor = "30623368939"
    db_session.commit()

    subtotales_ok = {
        "neto_gravado_21": 150000.00,
        "iva_21": 31500.00,
        "total": 181500.00
    }
    items_ok = [{
        "codigo_insumo": "MP-VET-098",
        "descripcion": "Principio Activo",
        "cantidad": 50.0,
        "precio_unitario": 3000.00
    }]

    # 1. Caso Straight Through Processing (STP) -> PROCESADA_LISTA_BATCH
    res_stp = evaluar_comprobante_integral(
        db_session,
        cabecera_ok,
        subtotales_ok,
        items_ok,
        confianza_global=0.98
    )
    assert res_stp["estado"] == EstadoComprobante.PROCESADA_LISTA_BATCH
    assert len(res_stp["alertas"]) == 0

    # 2. Caso Baja Confianza -> REQUIERE_AUDITORIA
    res_auditoria = evaluar_comprobante_integral(
        db_session,
        cabecera_ok,
        subtotales_ok,
        items_ok,
        confianza_global=0.85
    )
    assert res_auditoria["estado"] == EstadoComprobante.REQUIERE_AUDITORIA

    # 3. Caso Receptor Erróneo -> RECHAZADA
    cabecera_rechazo = dict(cabecera_ok, cuit_receptor="30111111118")
    res_rechazo = evaluar_comprobante_integral(
        db_session,
        cabecera_rechazo,
        subtotales_ok,
        items_ok
    )
    assert res_rechazo["estado"] == EstadoComprobante.RECHAZADA
