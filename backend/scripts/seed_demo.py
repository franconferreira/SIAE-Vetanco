"""
Script de Semilla y Generación de Facturas PDF de Demostración
[SIAE-Vetanco — Dirección de Proyectos Informáticos UADE]
1. Siembra los 20 Proveedores Recurrentes de Vetanco S.A.
2. Siembra el Maestro de Órdenes de Compra de SAP S/4HANA (Cierre Observación #12).
3. Genera 6 Facturas PDF Digitales AFIP/ARCA con diseño fidedigno cubriendo todos los casos UAT.
4. Procesa e ingesta los comprobantes en la BD de Staging SQLite.
5. Exporta 'data/maestro_oc_sap.csv' listo para probar la importación manual desde la WebApp.
"""
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import pymupdf as fitz

# Asegurar que el backend esté en el PYTHONPATH
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import DATA_DIR, PDF_STORAGE_DIR, INBOX_DROP_DIR
from app.database import init_db, SessionLocal
from app.models import (
    Proveedor,
    OrdenCompra,
    OrdenCompraItem,
    Comprobante,
    EstadoComprobante
)
from app.modules.supplier_templates import sembrar_proveedores_en_bd
from app.modules.mail_ingestor import procesar_comprobante_pdf


SAMPLE_PDFS_DIR = DATA_DIR / "sample_pdfs"
SAMPLE_PDFS_DIR.mkdir(parents=True, exist_ok=True)


def dibujar_factura_afip_digital(
    ruta_salida: Path,
    letra: str,
    tipo_comp_desc: str,
    punto_venta: int,
    numero_comp: int,
    cuit_emisor: str,
    razon_social: str,
    cuit_receptor: str,
    razon_social_receptor: str,
    orden_compra: str,
    items: list,
    neto_21: float,
    iva_21: float,
    percepcion_iibb: float,
    total: float,
    cae: str,
    vto_cae: str,
    moneda: str = "ARS",
    observacion_extra: str = ""
):
    """Genera un archivo PDF digital nativo con la estética oficial de comprobante electrónico AFIP."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # Tamaño A4

    # Recuadro exterior
    page.draw_rect(fitz.Rect(30, 30, 565, 812), color=(0.2, 0.2, 0.2), width=1)

    # Cabecera Letra (A, B, etc.)
    page.draw_rect(fitz.Rect(275, 30, 320, 75), color=(0.2, 0.2, 0.2), width=1)
    page.insert_text((287, 62), letra, fontsize=24, fontname="hebo")
    cod_afip = "001" if letra == "A" else "006"
    page.insert_text((282, 72), f"COD. {cod_afip}", fontsize=7, fontname="helv")

    # Emisor (Lado Izquierdo)
    page.insert_text((45, 55), razon_social[:36], fontsize=12, fontname="hebo")
    page.insert_text((45, 70), "Planta Industrial y Laboratorio Farmacéutico", fontsize=9, fontname="helv")
    page.insert_text((45, 85), f"CUIT: {cuit_emisor[:2]}-{cuit_emisor[2:10]}-{cuit_emisor[10]}", fontsize=9, fontname="helv")
    page.insert_text((45, 100), "Ingresos Brutos: Convenio Multilateral", fontsize=8, fontname="helv")
    page.insert_text((45, 115), "Inicio de Actividades: 01/03/1998", fontsize=8, fontname="helv")

    # Datos Factura (Lado Derecho)
    page.insert_text((340, 55), tipo_comp_desc, fontsize=13, fontname="hebo")
    pv_comp = f"{punto_venta:04d}-{numero_comp:08d}"
    page.insert_text((340, 75), f"Punto de Venta: {punto_venta:04d}  Comp. Nro: {numero_comp:08d}", fontsize=10, fontname="hebo")
    fecha_emision = datetime.today().strftime("%d/%m/%Y")
    page.insert_text((340, 95), f"Fecha de Emisión: {fecha_emision}", fontsize=9, fontname="helv")
    page.insert_text((340, 110), f"Moneda: {moneda}", fontsize=9, fontname="helv")

    # Línea divisoria cabecera
    page.draw_line(fitz.Point(30, 130), fitz.Point(565, 130), color=(0.2, 0.2, 0.2), width=1)

    # Datos Receptor
    page.insert_text((45, 148), "DATOS DEL RECEPTOR / CLIENTE:", fontsize=8, fontname="hebo")
    page.insert_text((45, 163), f"Razón Social: {razon_social_receptor}", fontsize=9, fontname="hebo")
    page.insert_text((45, 178), f"CUIT: {cuit_receptor}", fontsize=9, fontname="helv")
    page.insert_text((340, 163), "Condición IVA: IVA Responsable Inscripto", fontsize=9, fontname="helv")
    page.insert_text((340, 178), f"Orden de Compra: {orden_compra}", fontsize=9, fontname="hebo")

    # Línea divisoria items
    page.draw_line(fitz.Point(30, 195), fitz.Point(565, 195), color=(0.2, 0.2, 0.2), width=1)

    # Encabezado de Tabla de Ítems
    page.draw_rect(fitz.Rect(30, 200, 565, 220), color=(0.9, 0.9, 0.9), fill=(0.93, 0.93, 0.93))
    page.insert_text((40, 214), "Código", fontsize=8, fontname="hebo")
    page.insert_text((110, 214), "Descripción / Materia Prima", fontsize=8, fontname="hebo")
    page.insert_text((310, 214), "Cantidad", fontsize=8, fontname="hebo")
    page.insert_text((365, 214), "U.M.", fontsize=8, fontname="hebo")
    page.insert_text((410, 214), "Precio Unit.", fontsize=8, fontname="hebo")
    page.insert_text((495, 214), "Subtotal", fontsize=8, fontname="hebo")

    y = 238
    for it in items:
        page.insert_text((40, y), str(it["codigo"]), fontsize=8, fontname="helv")
        page.insert_text((110, y), str(it["descripcion"])[:38], fontsize=8, fontname="helv")
        page.insert_text((310, y), f"{it['cantidad']:.1f}", fontsize=8, fontname="helv")
        page.insert_text((365, y), str(it["unidad"]), fontsize=8, fontname="helv")
        page.insert_text((410, y), f"${it['precio']:,.2f}", fontsize=8, fontname="helv")
        page.insert_text((495, y), f"${it['subtotal']:,.2f}", fontsize=8, fontname="helv")
        y += 22

    # Línea divisoria pie impositivo
    page.draw_line(fitz.Point(30, 680), fitz.Point(565, 680), color=(0.2, 0.2, 0.2), width=1)

    # Subtotales
    page.insert_text((45, 700), f"Subtotal Neto Gravado: $ {neto_21:,.2f}", fontsize=9, fontname="helv")
    page.insert_text((45, 715), f"IVA 21%: $ {iva_21:,.2f}", fontsize=9, fontname="helv")
    if percepcion_iibb > 0:
        page.insert_text((45, 730), f"Percepción IIBB (Buenos Aires 3.5%): $ {percepcion_iibb:,.2f}", fontsize=9, fontname="helv")
    if observacion_extra:
        page.insert_text((45, 750), f"Observaciones: {observacion_extra}", fontsize=8, fontname="helv")

    # Total General
    page.draw_rect(fitz.Rect(350, 695, 550, 735), color=(0.1, 0.3, 0.6), fill=(0.95, 0.97, 1.0), width=1.5)
    page.insert_text((365, 720), f"Importe Total: $ {total:,.2f}", fontsize=13, fontname="hebo")

    # CAE AFIP al pie
    page.draw_line(fitz.Point(30, 765), fitz.Point(565, 765), color=(0.2, 0.2, 0.2), width=1)
    page.insert_text((45, 785), f"CAE N°: {cae}", fontsize=9, fontname="hebo")
    page.insert_text((45, 798), f"Fecha de Vto. de CAE: {vto_cae}", fontsize=9, fontname="helv")
    page.insert_text((350, 790), "Comprobante Autorizado por ARCA / AFIP", fontsize=8, fontname="helv")

    doc.save(str(ruta_salida))
    doc.close()


def sembrar_ordenes_compra(db):
    """Siembra Órdenes de Compra abiertas en Staging con sus posiciones de materia prima."""
    ocs_data = [
        {
            "numero_oc": "4500098124",
            "cuit_proveedor": "30708912014",
            "estado": "ABIERTA",
            "moneda": "ARS",
            "items": [
                {
                    "posicion_sap": "00010",
                    "codigo_insumo": "MP-VET-001",
                    "descripcion": "Principio Activo Ivermectina 99% USP",
                    "cantidad_pedida": 100.0,
                    "cantidad_remanente": 50.0,
                    "unidad_medida": "KG",
                    "precio_unitario": Decimal("3000.00"),
                    "cuenta_contable_sap": "11040010"
                }
            ]
        },
        {
            "numero_oc": "4500098125",
            "cuit_proveedor": "30708912022",
            "estado": "ABIERTA",
            "moneda": "ARS",
            "items": [
                {
                    "posicion_sap": "00010",
                    "codigo_insumo": "MP-VET-002",
                    "descripcion": "Excipientes Biológicos Adyuvantes",
                    "cantidad_pedida": 200.0,
                    "cantidad_remanente": 100.0,
                    "unidad_medida": "L",
                    "precio_unitario": Decimal("2000.00"),
                    "cuenta_contable_sap": "11040010"
                }
            ]
        },
        {
            "numero_oc": "4500098126",
            "cuit_proveedor": "30708912030",
            "estado": "ABIERTA",
            "moneda": "ARS",
            "items": [
                {
                    "posicion_sap": "00010",
                    "codigo_insumo": "MP-VET-003",
                    "descripcion": "Amoxicilina Trihidrato Polvo Oral",
                    "cantidad_pedida": 500.0,
                    "cantidad_remanente": 200.0,
                    "unidad_medida": "KG",
                    "precio_unitario": Decimal("4000.00"),  # Pactado a $4000
                    "cuenta_contable_sap": "11040010"
                }
            ]
        },
        {
            "numero_oc": "4500098127",
            "cuit_proveedor": "30708912049",
            "estado": "ABIERTA",
            "moneda": "ARS",
            "items": [
                {
                    "posicion_sap": "00010",
                    "codigo_insumo": "MP-VET-004",
                    "descripcion": "Frascos Ampolla Vidrio Tipo II 100ml",
                    "cantidad_pedida": 1000.0,
                    "cantidad_remanente": 100.0,  # Remanente solo 100 UN
                    "unidad_medida": "UN",
                    "precio_unitario": Decimal("500.00"),
                    "cuenta_contable_sap": "11040010"
                }
            ]
        },
        {
            "numero_oc": "4500098128",
            "cuit_proveedor": "30708912081",
            "estado": "ABIERTA",
            "moneda": "USD",
            "items": [
                {
                    "posicion_sap": "00010",
                    "codigo_insumo": "MP-VET-005",
                    "descripcion": "Principio Activo Albendazol Grado Vet",
                    "cantidad_pedida": 10.0,
                    "cantidad_remanente": 10.0,
                    "unidad_medida": "TN",
                    "precio_unitario": Decimal("1250.00"),
                    "cuenta_contable_sap": "11040010"
                }
            ]
        }
    ]

    for oc_dict in ocs_data:
        nro = oc_dict["numero_oc"]
        oc = db.query(OrdenCompra).filter(OrdenCompra.numero_oc == nro).first()
        if not oc:
            oc = OrdenCompra(
                numero_oc=nro,
                cuit_proveedor=oc_dict["cuit_proveedor"],
                estado=oc_dict["estado"],
                moneda=oc_dict["moneda"],
                centro_costo="PL01",
                fecha_emision=date.today()
            )
            db.add(oc)
            db.flush()

            for it in oc_dict["items"]:
                item_oc = OrdenCompraItem(
                    numero_oc=nro,
                    posicion_sap=it["posicion_sap"],
                    codigo_insumo=it["codigo_insumo"],
                    descripcion=it["descripcion"],
                    cantidad_pedida=it["cantidad_pedida"],
                    cantidad_remanente=it["cantidad_remanente"],
                    unidad_medida=it["unidad_medida"],
                    precio_unitario=it["precio_unitario"],
                    cuenta_contable_sap=it["cuenta_contable_sap"]
                )
                db.add(item_oc)
    db.commit()


def exportar_csv_maestro_oc():
    """Genera el archivo data/maestro_oc_sap.csv para probar la carga masiva desde la UI."""
    csv_path = DATA_DIR / "maestro_oc_sap.csv"
    filas = [
        "EBELN;LIFNR;razon_social;estado;moneda;centro_costo;MATNR;posicion_sap;descripcion;cantidad_pedida;cantidad_remanente;unidad_medida;precio_unitario;cuenta_contable;indicador_iva",
        "4500098124;30708912014;QUIMICA VETERINARIA ARGENTINA S.A.;ABIERTA;ARS;PL01;MP-VET-001;00010;Principio Activo Ivermectina 99% USP;100.0;50.0;KG;3000.00;11040010;V1",
        "4500098125;30708912022;BIOGENESIS INSUMOS FARMA S.R.L.;ABIERTA;ARS;PL01;MP-VET-002;00010;Excipientes Biológicos Adyuvantes;200.0;100.0;L;2000.00;11040010;V1",
        "4500098126;30708912030;DROGUERIA AGROVET INDUSTRIAL S.A.;ABIERTA;ARS;PL02;MP-VET-003;00010;Amoxicilina Trihidrato Polvo Oral;500.0;200.0;KG;4000.00;11040010;V1",
        "4500098127;30708912049;ENVASES FARMACEUTICOS DEL SUR S.A.;ABIERTA;ARS;PL01;MP-VET-004;00010;Frascos Ampolla Vidrio Tipo II 100ml;1000.0;100.0;UN;500.00;11040010;V1",
        "4500098128;30708912081;VET-PHARMA INTERNACIONAL S.A.;ABIERTA;USD;PL02;MP-VET-005;00010;Principio Activo Albendazol Grado Vet;10.0;10.0;TN;1250.00;11040010;V1"
    ]
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(filas) + "\n")


def ejecutar_seed():
    print("=" * 70)
    print("SEMBRANDO DATOS DE PRUEBA Y GENERANDO FACTURAS PDF — SIAE-VETANCO")
    print("=" * 70)

    init_db()
    db = SessionLocal()

    # 1. Sembrar 20 Proveedores
    prov_count = sembrar_proveedores_en_bd(db)
    print(f"[*] 20 Proveedores recurrentes verificados en Staging (Nuevos: {prov_count}).")

    # 2. Sembrar Órdenes de Compra abiertas en SAP
    sembrar_ordenes_compra(db)
    exportar_csv_maestro_oc()
    print("[*] Órdenes de Compra sembradas y 'data/maestro_oc_sap.csv' exportado.")

    # 3. Generar las 6 Facturas PDF Digitales representativas de todos los escenarios
    facturas_config = [
        # Caso 1: STP 100% (Straight Through Processing)
        {
            "filename": "1_stp_quimica_veterinaria.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 4,
            "nro": 12845,
            "cuit_emisor": "30708912014",
            "razon_social": "QUIMICA VETERINARIA ARGENTINA S.A.",
            "cuit_receptor": "30-62336893-9",
            "razon_receptor": "VETANCO S.A.",
            "oc": "4500098124",
            "items": [{"codigo": "MP-VET-001", "descripcion": "Principio Activo Ivermectina 99% USP", "cantidad": 50.0, "unidad": "KG", "precio": 3000.0, "subtotal": 150000.0}],
            "neto": 150000.0,
            "iva": 31500.0,
            "iibb": 0.0,
            "total": 181500.0,
            "cae": "74418901234567",
            "vto_cae": "24/10/2026",
            "moneda": "ARS",
            "nota": "Entrega conforme en Planta Vicente López."
        },
        # Caso 2: Requiere Auditoría por Discrepancia Impositiva y Percepción IIBB
        {
            "filename": "2_auditoria_discrepancia_biogenesis.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 2,
            "nro": 8432,
            "cuit_emisor": "30708912022",
            "razon_social": "BIOGENESIS INSUMOS FARMA S.R.L.",
            "cuit_receptor": "30-62336893-9",
            "razon_receptor": "VETANCO S.A.",
            "oc": "4500098125",
            "items": [{"codigo": "MP-VET-002", "descripcion": "Excipientes Biológicos Adyuvantes", "cantidad": 100.0, "unidad": "L", "precio": 2000.0, "subtotal": 200000.0}],
            "neto": 200000.0,
            "iva": 42000.0,
            "iibb": 7000.0,
            "total": 255000.0,  # Discrepancia intencional: suma da 249000, total dice 255000 (+6000)
            "cae": "74421199887766",
            "vto_cae": "28/10/2026",
            "moneda": "ARS",
            "nota": "Lote B-9912. Percepción IIBB sujeta a revisión analista."
        },
        # Caso 3: Requiere Auditoría por Sobreprecio en OC (Factura $4500 vs $4000 en OC)
        {
            "filename": "3_auditoria_sobreprecio_agrovet.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 5,
            "nro": 34120,
            "cuit_emisor": "30708912030",
            "razon_social": "DROGUERIA AGROVET INDUSTRIAL S.A.",
            "cuit_receptor": "30-62336893-9",
            "razon_receptor": "VETANCO S.A.",
            "oc": "4500098126",
            "items": [{"codigo": "MP-VET-003", "descripcion": "Amoxicilina Trihidrato Polvo Oral", "cantidad": 50.0, "unidad": "KG", "precio": 4500.0, "subtotal": 225000.0}],
            "neto": 225000.0,
            "iva": 47250.0,
            "iibb": 0.0,
            "total": 272250.0,
            "cae": "74435566778899",
            "vto_cae": "30/10/2026",
            "moneda": "ARS",
            "nota": "Ajuste de lista de precios no homologado en OC."
        },
        # Caso 4: Requiere Auditoría por Exceso de Cantidad respecto a Saldo Remanente OC
        {
            "filename": "4_auditoria_exceso_cantidad_envases.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 1,
            "nro": 55102,
            "cuit_emisor": "30708912049",
            "razon_social": "ENVASES FARMACEUTICOS DEL SUR S.A.",
            "cuit_receptor": "30-62336893-9",
            "razon_receptor": "VETANCO S.A.",
            "oc": "4500098127",
            "items": [{"codigo": "MP-VET-004", "descripcion": "Frascos Ampolla Vidrio Tipo II 100ml", "cantidad": 250.0, "unidad": "UN", "precio": 500.0, "subtotal": 125000.0}],
            "neto": 125000.0,
            "iva": 26250.0,
            "iibb": 0.0,
            "total": 151250.0,
            "cae": "74441122334455",
            "vto_cae": "31/10/2026",
            "moneda": "ARS",
            "nota": "Entrega de remesa total de envases."
        },
        # Caso 5: Rechazo Automático — Factura no pertenece a Vetanco S.A. (RF-14)
        {
            "filename": "5_rechazo_cuit_ajeno_sintesis.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 3,
            "nro": 99201,
            "cuit_emisor": "30708912073",
            "razon_social": "SINTESIS QUIMICA INDUSTRIAL S.A.",
            "cuit_receptor": "30-11111111-8",  # Receptor ajeno
            "razon_receptor": "OTRA EMPRESA AGROPECUARIA S.A.",
            "oc": "OC-AJENA-99",
            "items": [{"codigo": "MP-SOLV-01", "descripcion": "Propilenglicol Grado USP", "cantidad": 200.0, "unidad": "L", "precio": 1500.0, "subtotal": 300000.0}],
            "neto": 300000.0,
            "iva": 63000.0,
            "iibb": 0.0,
            "total": 363000.0,
            "cae": "74459988776655",
            "vto_cae": "05/11/2026",
            "moneda": "ARS",
            "nota": "Factura enviada por error de casilla al buzón de Vetanco."
        },
        # Caso 6: Factura en Moneda Extranjera (USD)
        {
            "filename": "6_stp_usd_vetpharma.pdf",
            "letra": "A",
            "tipo_desc": "FACTURA A",
            "pv": 3,
            "nro": 1950,
            "cuit_emisor": "30708912081",
            "razon_social": "VET-PHARMA INTERNACIONAL S.A.",
            "cuit_receptor": "30-62336893-9",
            "razon_receptor": "VETANCO S.A.",
            "oc": "4500098128",
            "items": [{"codigo": "MP-VET-005", "descripcion": "Principio Activo Albendazol Grado Vet", "cantidad": 10.0, "unidad": "TN", "precio": 1250.0, "subtotal": 12500.0}],
            "neto": 12500.0,
            "iva": 2625.0,
            "iibb": 0.0,
            "total": 15125.0,
            "cae": "74467788990011",
            "vto_cae": "10/11/2026",
            "moneda": "USD",
            "nota": "Insumo importado despacho aduanero 26001IC04."
        }
    ]

    print("\n[*] Generando 6 Facturas PDF Digitales AFIP e ingiriéndolas en Staging:")
    for cfg in facturas_config:
        pdf_path = SAMPLE_PDFS_DIR / cfg["filename"]
        dibujar_factura_afip_digital(
            ruta_salida=pdf_path,
            letra=cfg["letra"],
            tipo_comp_desc=cfg["tipo_desc"],
            punto_venta=cfg["pv"],
            numero_comp=cfg["nro"],
            cuit_emisor=cfg["cuit_emisor"],
            razon_social=cfg["razon_social"],
            cuit_receptor=cfg["cuit_receptor"],
            razon_social_receptor=cfg["razon_receptor"],
            orden_compra=cfg["oc"],
            items=cfg["items"],
            neto_21=cfg["neto"],
            iva_21=cfg["iva"],
            percepcion_iibb=cfg["iibb"],
            total=cfg["total"],
            cae=cfg["cae"],
            vto_cae=cfg["vto_cae"],
            moneda=cfg["moneda"],
            observacion_extra=cfg["nota"]
        )

        # Ingerir en Staging usando el flujo formal
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        msg_id = f"DEMO_SEED_{cfg['filename']}"
        ok, msg, comp = procesar_comprobante_pdf(
            db=db,
            pdf_bytes=pdf_bytes,
            nombre_archivo_original=cfg["filename"],
            message_id=msg_id,
            remitente="proveedor.demo@vetanco.com",
            asunto=f"Factura {cfg['razon_social']}"
        )
        estado_badge = comp.estado.value if comp else "ERROR"
        print(f"    -> [{estado_badge}] {cfg['filename']}: {msg}")

    # También dejamos una copia de una factura limpia en 'data/casilla_entrante/'
    # para que en la defensa o prueba se pueda presionar 'Sincronizar Gmail / Casilla' y verla entrar en vivo
    casilla_demo_pdf = INBOX_DROP_DIR / "factura_entrante_en_vivo_quimica.pdf"
    if not casilla_demo_pdf.exists():
        src_pdf = SAMPLE_PDFS_DIR / "1_stp_quimica_veterinaria.pdf"
        if src_pdf.exists():
            with open(src_pdf, "rb") as sf, open(casilla_demo_pdf, "wb") as df:
                df.write(sf.read())
            print(f"[*] Se preparó '{casilla_demo_pdf.name}' en 'data/casilla_entrante/' para demo en vivo.")

    total_comprobantes = db.query(Comprobante).count()
    print(f"\n[OK] Base de datos de Staging lista con {total_comprobantes} comprobantes listos para el Dashboard y Split-View.")
    print("=" * 70)
    db.close()


if __name__ == "__main__":
    ejecutar_seed()
