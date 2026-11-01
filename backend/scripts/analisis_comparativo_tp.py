"""
Script de Ingesta Masiva y Análisis Comparativo de Incongruencias
Audita los 26 PDFs de las carpetas 'Junio 2026' y 'Mayo' contra el Ground Truth
"""
import sys
import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

# Ajustar PYTHONPATH
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import fitz
import winocr
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Comprobante, EstadoComprobante
from app.modules.mail_ingestor import procesar_comprobante_pdf, calcular_sha256
from app.modules.validators import limpiar_cuit, a_decimal

TP_DIR = Path(r"F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco\TP Facturas")

async def get_ocr_text(doc):
    ocr_lines = []
    for page in doc:
        pix = page.get_pixmap(dpi=150, alpha=True)
        res = await winocr.recognize_bytes(pix.samples, pix.width, pix.height, lang="es")
        ocr_lines.append(res.text)
    return "\n\n".join(ocr_lines)


def get_ground_truth(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    text_digital = ""
    for page in doc:
        text_digital += "\n" + page.get_text()
    
    # Si tiene menos de 40 caracteres, usar OCR
    if len(text_digital.strip()) < 40:
        raw_text = asyncio.run(get_ocr_text(doc))
        es_escaneado = True
    else:
        raw_text = text_digital
        es_escaneado = False
    doc.close()

    # Normalizar espacios
    t = raw_text

    # 1. CUIT Emisor y Receptor
    # Buscar todos los CUITs en el documento
    all_cuits = []
    for m in re.finditer(r"\b(20|23|24|27|30|33)[-\s]?[0-9]{8}[-\s]?[0-9]\b", t):
        c = re.sub(r"\D", "", m.group(0))
        if c not in all_cuits:
            all_cuits.append(c)

    cuit_vetanco_oficial = "30623368939"
    cuit_vetanco_real = "30623368935"
    cuit_receptor = None
    cuit_emisor = None

    for c in all_cuits:
        if c in (cuit_vetanco_oficial, cuit_vetanco_real):
            cuit_receptor = c
        elif not cuit_emisor:
            cuit_emisor = c

    # 2. Letra y Tipo
    letra = "A"
    tipo = "001"
    if "FACTURA C" in t.upper() or "COD. 011" in t.upper() or "COD. 11" in t.upper() or "CODIGO 11" in t.upper():
        letra = "C"
        tipo = "011"
    elif "FACTURA B" in t.upper() or "COD. 006" in t.upper() or "COD. 06" in t.upper() or "CODIGO 06" in t.upper():
        letra = "B"
        tipo = "006"
    elif "NOTA DE CRÉDITO" in t.upper() or "NOTA DE CREDITO" in t.upper():
        if " C" in t.upper():
            letra = "C"
            tipo = "013"
        elif " B" in t.upper():
            letra = "B"
            tipo = "008"
        else:
            letra = "A"
            tipo = "003"
    elif "NOTA DE DÉBITO" in t.upper() or "NOTA DE DEBITO" in t.upper():
        letra = "A"
        tipo = "002"

    # 3. Punto de Venta y Número
    pv = None
    nro = None
    m_pv_comp = re.search(r"(?:Punto de Venta|Nro\.?\s*Comp\.?|Comp\.?\s*Nro\.?|N[úu]mero)[\s:]*([0-9]{1,5})[\s\-_/]+([0-9]{1,8})", t, re.IGNORECASE)
    if m_pv_comp:
        pv = int(m_pv_comp.group(1))
        nro = int(m_pv_comp.group(2))
    else:
        m_guion = re.search(r"\b([0-9]{4,5})-([0-9]{5,8})\b", t)
        if m_guion:
            pv = int(m_guion.group(1))
            nro = int(m_guion.group(2))

    # 4. CAE y Vencimiento CAE
    cae = None
    vto_cae = None
    m_cae = re.search(r"CAE\s*(?:N[°o\.]*|NO)?[\s:]*([0-9]{14})", t, re.IGNORECASE)
    if m_cae:
        cae = m_cae.group(1)
    
    m_vto = re.search(r"(?:Fecha\s*(?:de\s*)?vto\.?(?:\s*de\s*CAE)?|Vencimiento\s*(?:CAE|CAI)?)[\s:]*([0-9]{1,2}\s*[/ -]\s*[0-9]{1,2}\s*[/ -]\s*[0-9]{4})", t, re.IGNORECASE)
    if m_vto:
        fv_clean = m_vto.group(1).replace(" ", "").replace("-", "/")
        try:
            vto_cae = datetime.strptime(fv_clean, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    # 5. Fecha Emisión
    fecha_emision = None
    m_fe = re.search(r"(?:Buenos Aires,?\s*|Fecha\s*(?:de\s*Emisi[oó]n)?[\s:]*)([0-9]{1,2}\s*[/ -]\s*[0-9]{1,2}\s*[/ -]\s*[0-9]{4})", t, re.IGNORECASE)
    if m_fe:
        fe_clean = m_fe.group(1).replace(" ", "").replace("-", "/")
        try:
            fecha_emision = datetime.strptime(fe_clean, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    # 6. Total
    total = None
    # Buscar patrones como Total: $ 1.234,56 o Importe Total: $ 1.234,56
    m_tot = re.search(r"(?:Importe\s*Total|TOTAL\s*A\s*PAGAR|TOTAL\s*GENERAL|TOTAL\s*[\$]|Total:)[\s\$\S]{0,25}?([0-9]{1,3}(?:[,\.][0-9]{3})*[,\.][0-9]{2})", t, re.IGNORECASE)
    if m_tot:
        s = m_tot.group(1).replace(" ", "").replace("$", "")
        if "," in s and "." in s:
            if s.find(",") < s.find("."):
                s = s.replace(",", "")
            else:
                s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            total = float(s)
        except Exception:
            pass

    # 7. Orden de Compra
    oc = None
    m_oc = re.search(r"\b(?:OC|Orden de Compra|Pedido|O\.C\.|DOC\s*\.?\s*INT\s*\.?|NRO\s*\.?\s*PEDIDO)[\s\.:#N°\-_]*([0-9]{5,20})\b", t, re.IGNORECASE)
    if m_oc:
        oc = m_oc.group(1)
    if not oc:
        m_sap = re.search(r"\b(4[5-7][0-9]{8}|54[0-9]{8})\b", t)
        if m_sap:
            oc = m_sap.group(1)

    # 8. Razón Social
    rs = None
    if "SEIDOR" in t.upper():
        rs = "SEIDOR TECHNOLOGIES S.A."
    elif "CLARO" in t.upper() or "AMX ARGENTINA" in t.upper():
        rs = "AMX ARGENTINA S.A. (CLARO)"
    elif "EVEREST" in t.upper():
        rs = "EVEREST INSURANCE / EVEREST S.A."
    elif "NETLATIN" in t.upper():
        rs = "Netlatin S.R.L."
    elif "DATACLOUD" in t.upper():
        rs = "DATACLOUD S.A."
    elif "GS1" in t.upper():
        rs = "GS1 ARGENTINA"
    elif "MORENO" in t.upper() and "YANINA" in t.upper():
        rs = "MORENO YANINA ANDREA"
    elif "GUSTAVO" in t.upper() and "PANZITTA" in t.upper():
        rs = "GUSTAVO A. I. PANZITTA"
    elif "AUDITECOM" in t.upper():
        rs = "AUDITECOM SRL"
    elif "BOSIO" in t.upper():
        rs = "BOSIO HNOS S.A."

    return {
        "es_escaneado": es_escaneado,
        "cuit_emisor": cuit_emisor,
        "cuit_receptor": cuit_receptor,
        "razon_social": rs,
        "letra": letra,
        "tipo_comprobante": tipo,
        "punto_venta": pv,
        "numero_comprobante": nro,
        "fecha_emision": fecha_emision,
        "cae": cae,
        "vencimiento_cae": vto_cae,
        "total": total,
        "orden_compra": oc,
        "raw_text_len": len(t)
    }


def ejecutar_auditoria():
    db = SessionLocal()
    folders = [
        ("Junio 2026", TP_DIR / "Junio 2026"),
        ("Mayo", TP_DIR / "Mayo")
    ]

    all_pdf_paths = []
    for fol_name, fol_path in folders:
        for p in fol_path.glob("**/*"):
            if p.is_file() and p.suffix.lower() == ".pdf":
                all_pdf_paths.append((fol_name, p))

    print(f"=================================================================")
    print(f"AUDITORIA MASIVA DE {len(all_pdf_paths)} FACTURAS REALES EN TP FACTURAS")
    print(f"=================================================================\n")

    resultados = []

    for idx, (fol_name, pdf_path) in enumerate(all_pdf_paths, 1):
        rel_path = pdf_path.relative_to(TP_DIR)
        print(f"[{idx:02d}/{len(all_pdf_paths):02d}] Procesando: {rel_path} ...", end=" ", flush=True)

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        sha256 = calcular_sha256(pdf_bytes)

        # 1. Ejecutar procesamiento del programa
        ok, mensaje, comp = procesar_comprobante_pdf(
            db=db,
            pdf_bytes=pdf_bytes,
            nombre_archivo_original=pdf_path.name,
            message_id=f"TP_BENCHMARK_{idx}_{sha256[:8]}"
        )

        # Si ya existía por hash o tupla, buscar el comprobante correspondiente en BD
        if not comp:
            comp = db.query(Comprobante).filter(Comprobante.sha256_hash == sha256).first()

        # 2. Análisis Ground Truth independiente
        gt = get_ground_truth(pdf_path)

        # 3. Detectar incongruencias
        incongruencias = []
        prog_data = {}

        if comp:
            prog_data = {
                "id": comp.id,
                "cuit_emisor": comp.cuit_emisor,
                "razon_social": comp.razon_social_emisor,
                "letra": comp.letra,
                "tipo_comprobante": comp.tipo_comprobante,
                "punto_venta": comp.punto_venta,
                "numero_comprobante": comp.numero_comprobante,
                "fecha_emision": comp.fecha_emision.strftime("%Y-%m-%d") if comp.fecha_emision else None,
                "cae": comp.cae,
                "vencimiento_cae": comp.vencimiento_cae.strftime("%Y-%m-%d") if comp.vencimiento_cae else None,
                "total": float(comp.importe_total) if comp.importe_total is not None else 0.0,
                "orden_compra": comp.orden_compra_nro,
                "estado": comp.estado.value if hasattr(comp.estado, "value") else str(comp.estado),
                "alertas": [a.get("codigo") for a in comp.alertas_validacion] if comp.alertas_validacion else []
            }

            # Comparación campo a campo
            if gt["cuit_emisor"] and prog_data["cuit_emisor"] != gt["cuit_emisor"]:
                incongruencias.append(f"CUIT Emisor difiere: Programa={prog_data['cuit_emisor']} vs GroundTruth={gt['cuit_emisor']}")

            if gt["punto_venta"] and prog_data["punto_venta"] != gt["punto_venta"]:
                incongruencias.append(f"Punto de Venta difiere: Programa={prog_data['punto_venta']} vs GroundTruth={gt['punto_venta']}")

            if gt["numero_comprobante"] and prog_data["numero_comprobante"] != gt["numero_comprobante"]:
                incongruencias.append(f"Nro Comprobante difiere: Programa={prog_data['numero_comprobante']} vs GroundTruth={gt['numero_comprobante']}")

            if gt["cae"] and prog_data["cae"] != gt["cae"]:
                incongruencias.append(f"CAE difiere: Programa={prog_data['cae']} vs GroundTruth={gt['cae']}")

            if gt["total"] and abs(prog_data["total"] - gt["total"]) > 0.05:
                incongruencias.append(f"Total difiere: Programa=${prog_data['total']} vs GroundTruth=${gt['total']}")

            if gt["orden_compra"] and prog_data["orden_compra"] != gt["orden_compra"]:
                incongruencias.append(f"Orden de Compra difiere: Programa={prog_data['orden_compra']} vs GroundTruth={gt['orden_compra']}")
        else:
            incongruencias.append(f"El programa descartó el comprobante: {mensaje}")

        status_str = "OK (Sin discrepancias)" if len(incongruencias) == 0 else f"{len(incongruencias)} incongruencias"
        print(f"[{status_str}]")

        resultados.append({
            "archivo": str(rel_path),
            "nombre": pdf_path.name,
            "carpeta": fol_name,
            "es_escaneado": gt["es_escaneado"],
            "programa": prog_data,
            "ground_truth": gt,
            "incongruencias": incongruencias,
            "mensaje_ingesta": mensaje
        })

    db.close()

    # Guardar reporte JSON completo
    report_file = BACKEND_DIR / "data" / "reporte_auditoria_tp.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n=================================================================")
    print(f"REPORTE GUARDADO EN: {report_file}")
    print(f"Total procesados: {len(resultados)}")
    total_con_incongruencias = sum(1 for r in resultados if len(r["incongruencias"]) > 0)
    print(f"Facturas con incongruencias detectadas: {total_con_incongruencias}")
    print(f"Facturas con coincidencia exacta (100%): {len(resultados) - total_con_incongruencias}")
    print(f"=================================================================")

if __name__ == "__main__":
    ejecutar_auditoria()
