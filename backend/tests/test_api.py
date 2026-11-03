import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Comprobante, EstadoComprobante, AuditoriaLog

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_audit_comprobante():
    db = SessionLocal()
    audit_exists = db.query(Comprobante).filter(Comprobante.estado == EstadoComprobante.REQUIERE_AUDITORIA).first()
    if not audit_exists:
        comp = db.query(Comprobante).filter(Comprobante.estado != EstadoComprobante.RECHAZADA).first()
        if comp:
            comp.estado = EstadoComprobante.REQUIERE_AUDITORIA
            comp.alertas_validacion = [{
                "codigo": "DISCREPANCIA_SUMA_IMPOSITIVA",
                "campo": "total",
                "mensaje": "Discrepancia en suma impositiva",
                "severidad": "error"
            }]
            db.commit()
    db.close()


def test_api_dashboard_resumen():
    response = client.get("/api/dashboard/resumen")
    assert response.status_code == 200
    data = response.json()
    assert "total_recibidas_hoy" in data
    assert "porcentaje_stp" in data
    assert "pendientes_auditoria" in data
    assert "monto_lote_ars" in data
    assert data["pendientes_auditoria"] >= 1


def test_api_listar_comprobantes_con_filtros():
    # 1. Listar todos
    res_all = client.get("/api/comprobantes")
    assert res_all.status_code == 200
    facturas = res_all.json()
    assert len(facturas) >= 6

    # 2. Filtrar por estado REQUIERE_AUDITORIA
    res_audit = client.get("/api/comprobantes?estado=REQUIERE_AUDITORIA")
    assert res_audit.status_code == 200
    for f in res_audit.json():
        assert f["estado"] == "REQUIERE_AUDITORIA"

    # 3. Filtrar por búsqueda
    res_search = client.get("/api/comprobantes?search=Quimica")
    assert res_search.status_code == 200
    assert len(res_search.json()) >= 1


def test_api_visor_pdf():
    # Obtener el primer comprobante para consultar su PDF
    res = client.get("/api/comprobantes")
    primer_id = res.json()[0]["id"]

    res_pdf = client.get(f"/api/comprobantes/{primer_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 100


def test_api_aprobacion_1click_con_audit_trail():
    # Tomar la factura que tiene discrepancia impositiva para corregirla y aprobarla
    res = client.get("/api/comprobantes?estado=REQUIERE_AUDITORIA")
    facturas_audit = res.json()
    assert len(facturas_audit) > 0
    factura = facturas_audit[0]
    factura_id = factura["id"]

    # Calcular la suma corregida para que dé exacto
    neto = Decimal(str(factura["neto_gravado_21"]))
    iva = Decimal(str(factura["iva_21"]))
    iibb = Decimal(str(factura["percepcion_iibb"]))
    total_corregido = float(neto + iva + iibb)

    payload = {
        "neto_gravado_21": float(neto),
        "iva_21": float(iva),
        "percepcion_iibb": float(iibb),
        "importe_total": total_corregido,
        "usuario": "franco.analista"
    }

    # Ejecutar aprobación 1-Click
    res_aprob = client.put(f"/api/comprobantes/{factura_id}/aprobar", json=payload)
    assert res_aprob.status_code == 200
    data_aprobada = res_aprob.json()
    assert data_aprobada["estado"] == "APROBADA_POR_USUARIO"

    # Verificar que se haya registrado en AuditoriaLog
    db = SessionLocal()
    logs = db.query(AuditoriaLog).filter(AuditoriaLog.comprobante_id == factura_id).all()
    assert len(logs) >= 1
    assert any(l.accion == "APROBACION_1CLICK" for l in logs)
    db.close()


def test_api_generar_y_listar_batch():
    # Asegurar al menos una factura lista para consolidar en el lote
    db = SessionLocal()
    comp_listo = db.query(Comprobante).filter(
        Comprobante.estado.in_([EstadoComprobante.PROCESADA_LISTA_BATCH, EstadoComprobante.APROBADA_POR_USUARIO]),
        Comprobante.lote_batch_id.is_(None)
    ).first()
    if not comp_listo:
        comp_candidate = db.query(Comprobante).filter(Comprobante.estado != EstadoComprobante.RECHAZADA).first()
        if comp_candidate:
            comp_candidate.estado = EstadoComprobante.PROCESADA_LISTA_BATCH
            comp_candidate.lote_batch_id = None
            db.commit()
    db.close()

    # Generar Lote Batch
    res_gen = client.post("/api/batch/generar")
    assert res_gen.status_code == 200
    lote = res_gen.json()
    assert lote["id"] > 0
    assert lote["cantidad_facturas"] >= 1
    assert "LOTE_SAP_VETANCO_" in lote["nombre_archivo"]

    # Previsualizar Lote
    res_prev = client.get(f"/api/batch/{lote['id']}/preview")
    assert res_prev.status_code == 200
    assert "01;KR;AR01;" in res_prev.json()["contenido"]

    # Descargar Lote CSV
    res_down = client.get(f"/api/batch/{lote['id']}/descargar")
    assert res_down.status_code == 200
    assert res_down.headers["content-type"].startswith("text/csv")


def test_api_ordenes_compra_y_proveedores():
    res_ocs = client.get("/api/ordenes-compra")
    assert res_ocs.status_code == 200
    assert len(res_ocs.json()) >= 5

    res_provs = client.get("/api/proveedores")
    assert res_provs.status_code == 200
    assert len(res_provs.json()) == 20


def test_api_eliminar_comprobante():
    # 1. Crear o tomar un comprobante para eliminar
    res_list = client.get("/api/comprobantes")
    assert res_list.status_code == 200
    comprobantes = res_list.json()
    assert len(comprobantes) > 0

    target_id = comprobantes[-1]["id"]

    # 2. Eliminarlo vía DELETE
    res_del = client.delete(f"/api/comprobantes/{target_id}")
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True

    # 3. Verificar que ya no existe (404)
    res_get = client.get(f"/api/comprobantes/{target_id}")
    assert res_get.status_code == 404
