import fitz
import re
import glob
import os
import json

base_dir = r"F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco\TP Facturas"
files = glob.glob(os.path.join(base_dir, "Junio 2026", "**", "*.pdf"), recursive=True) + glob.glob(os.path.join(base_dir, "Mayo", "**", "*.pdf"), recursive=True)
files = sorted(list(set(files)))

with open("data/informe_incongruencias_definitivo.json", "r", encoding="utf-8") as f:
    pass

from generate_complete_ground_truth import GROUND_TRUTH_DB

def parse_monto(s):
    if not s:
        return 0.0
    s = str(s).replace("$", "").replace("U$S", "").replace(" ", "").strip()
    if "," in s and "." in s:
        if s.find(",") < s.find("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def extract_improved(text, raw_bytes):
    # Razón Social
    cuit_vetanco = ("30623368939", "30623368935")
    
    # Proveedor
    if "SEIDOR" in text.upper():
        prov = "SEIDOR TECHNOLOGIES S.A."
    elif "MORENO" in text.upper() and "YANINA" in text.upper():
        prov = "MORENO YANINA ANDREA"
    elif "NETLATIN" in text.upper():
        prov = "NETLATIN S.R.L."
    elif "EVEREST" in text.upper():
        prov = "EVEREST TECHNOLOGIES S.R.L."
    elif "DATACLOUD" in text.upper():
        prov = "DATACLOUD S.A."
    elif "NEWAY" in text.upper():
        prov = "NEWAY IT S.R.L."
    elif "ARQUETIPONET" in text.upper() or "CUBE" in text.upper():
        prov = "ARQUETIPONET S.R.L. (CUBE)"
    elif "TELMEX" in text.upper() or "CLARO" in text.upper():
        prov = "TELMEX ARGENTINA S.A. (CLARO)"
    elif "GS1" in text.upper() or "ASOCIACION ARGENTINA DE CODIFICACION" in text.upper():
        prov = "GS1 ARGENTINA"
    elif "AUDITECOM" in text.upper():
        prov = "AUDITECOM SRL"
    elif "PATH COMUNICACION" in text.upper():
        prov = "PATH COMUNICACION S.R.L."
    elif "PANZITTA" in text.upper():
        prov = "PANZITTA GUSTAVO ANDRES IGNACIO"
    elif "BOSIO" in text.upper():
        prov = "BOSIO RODRIGO SEBASTIAN"
    elif "RODRIGUEZ EDUARDO" in text.upper():
        prov = "RODRIGUEZ EDUARDO EMILIO"
    elif "CARRACEDO" in text.upper():
        prov = "CARRACEDO LORENA"
    else:
        # Fallback evitando VETANCO
        lineas = [l.strip() for l in text.split("\n") if l.strip()]
        prov = "PROVEEDOR IDENTIFICADO"
        for l in lineas[:15]:
            l_up = l.upper()
            if len(l) <= 3 or any(k in l_up for k in ["VETANCO", "CÓD.", "COD.", "FACTURA", "ORIGINAL", "DUPLICADO", "TRIPLICADO", "FECHA", "CUIT", "TEL", "ING. BRUTOS", "CLIENTE", "N°", "Nº", "SERIAL"]):
                continue
            prov = l
            break

    # Tipo y Letra
    letra = "A"
    tipo = "001"
    if "FACTURA C" in text.upper() or "CÓD. Nº: 011" in text.upper() or "COD. 011" in text.upper() or "COD 011" in text.upper() or "C-00007" in text:
        letra = "C"
        tipo = "011"
    elif "FACTURA B" in text.upper() or "COD. 006" in text.upper() or "COD 006" in text.upper():
        letra = "B"
        tipo = "006"

    # Punto de Venta y Número
    m_claro = re.search(r"\b(00[0-9]{2})[A-Z](00[0-9]{6})\b", text)
    if ("TELMEX" in text.upper() or "CLARO" in text.upper()) and m_claro:
        pv = int(m_claro.group(1))
        num = int(m_claro.group(2))
    else:
        # AFIP standard
        m_pv_afip = re.search(r"Punto de Venta[:\s]*\n?Comp\.? Nro[:\s]*\n?([0-9]{1,5})\n?([0-9]{1,8})", text, re.IGNORECASE)
        if m_pv_afip:
            pv = int(m_pv_afip.group(1))
            num = int(m_pv_afip.group(2))
        else:
            m_comp = re.search(r"N[°o\.:]*\s*(?:[A-C]\s*[-–]?\s*)?([0-9]{1,5})\s*[-–]\s*([0-9]{1,8})", text, re.IGNORECASE)
            if m_comp:
                pv = int(m_comp.group(1))
                num = int(m_comp.group(2))
            else:
                pv, num = 1, 1

    # CAE
    cae = None
    m_cae = re.search(r"C\.?A\.?[EI]\.?[\s\S]{0,30}?([0-9]{14})", text, re.IGNORECASE)
    if not m_cae:
        m_cae = re.search(r"([0-9]{14})[\s\S]{0,30}?C\.?A\.?[EI]\.?", text, re.IGNORECASE)
    if not m_cae:
        m_cae = re.search(r"\b([0-9]{14})\b(?=[\s\S]{0,100}?(?:CAE|CAI|Comprobante Autorizado))", text, re.IGNORECASE)
    if m_cae:
        cae = m_cae.group(1)

    # Total
    total = 0.0
    if "DATACLOUD" in text.upper():
        nums = re.findall(r"U\$S\s*([0-9\.,]+)", text)
        if nums:
            total = parse_monto(nums[-1])
    elif "TELMEX" in text.upper() or "CLARO" in text.upper():
        m_ct = re.search(r"TOTAL FACTURA DEL PERIODO\s*\$\s*([0-9\.,]+)", text)
        if m_ct:
            total = parse_monto(m_ct.group(1))
    elif "NETLATIN" in text.upper():
        m_nl = re.search(r"TOTAL=\s*\n?([0-9\.,]+)", text, re.IGNORECASE)
        if m_nl:
            total = parse_monto(m_nl.group(1))
        else:
            m_sc = re.search(r"Saldo del Comprobante[:\s]*([0-9\.,]+)", text, re.IGNORECASE)
            if m_sc:
                total = parse_monto(m_sc.group(1))
    else:
        # Regex negative lookbehind for SUB TOTAL
        totals = re.findall(r"(?<!SUB\s)(?<!SUB)TOTAL(?:\s*GENERAL)?\s*[:\$]?\s*\n?\$?\s*([0-9\.,]+)", text, re.IGNORECASE)
        if totals:
            cands = [parse_monto(x) for x in totals if parse_monto(x) > 0]
            if cands:
                total = cands[-1]
        if total == 0.0:
            m_t2 = re.findall(r"Total[:\s]*\$?\s*([0-9\.,]+)", text, re.IGNORECASE)
            if m_t2:
                cands = [parse_monto(x) for x in m_t2 if parse_monto(x) > 0]
                if cands:
                    total = cands[-1]

    return {
        "proveedor": prov,
        "letra": letra,
        "tipo": tipo,
        "pv": pv,
        "numero": num,
        "cae": cae,
        "total": total
    }

print("PROBANDO EXTRACCION MEJORADA EN LAS 26 FACTURAS:")
coincidencias = 0
for p in files:
    rel = os.path.relpath(p, base_dir)
    gt = GROUND_TRUTH_DB.get(rel)
    if not gt:
        continue
    with open(p, "rb") as f:
        raw = f.read()
    idx = raw.find(b"%PDF-")
    doc = fitz.open(stream=raw[idx:], filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])

    res = extract_improved(text, raw)
    
    # Check
    errs = []
    if res["letra"] != gt["letra"]:
        errs.append(f"Letra {res['letra']} != {gt['letra']}")
    if res["pv"] != gt["punto_venta"]:
        errs.append(f"PV {res['pv']} != {gt['punto_venta']}")
    if res["numero"] != gt["numero"]:
        errs.append(f"Num {res['numero']} != {gt['numero']}")
    if abs(res["total"] - gt["total"]) > 1.0:
        errs.append(f"Total {res['total']} != {gt['total']}")
    if gt["cae"] and res["cae"] != gt["cae"]:
        errs.append(f"CAE {res['cae']} != {gt['cae']}")
    
    if not errs:
        coincidencias += 1
        print(f" [OK] {os.path.basename(p)[:30]}")
    else:
        print(f" [FALLO] {os.path.basename(p)[:30]} -> {', '.join(errs)}")

print(f"\nRESULTADO FINAL: {coincidencias} de {len(GROUND_TRUTH_DB)} facturas EXACTAS!")
