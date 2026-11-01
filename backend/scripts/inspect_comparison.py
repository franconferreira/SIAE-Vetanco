import os
import glob
import re
import json
import fitz

base_dir = r"F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco\TP Facturas"
target_dirs = [os.path.join(base_dir, "Junio 2026"), os.path.join(base_dir, "Mayo")]

pdf_files = []
for d in target_dirs:
    for root, _, files in os.walk(d):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))
pdf_files = sorted(list(set(pdf_files)))

with open("data/reporte_auditoria_tp.json", "r", encoding="utf-8") as f:
    reporte = json.load(f)

reporte_map = {}
for item in reporte:
    reporte_map[os.path.normpath(item["archivo"])] = item

for idx, p in enumerate(pdf_files, 1):
    rel = os.path.relpath(p, base_dir)
    norm_rel = os.path.normpath(rel)
    rep_item = reporte_map.get(norm_rel, {})
    p_data = rep_item.get("programa", {})
    incongruencias = rep_item.get("incongruencias", [])
    msg = rep_item.get("mensaje_ingesta", "")

    cuit = p_data.get("cuit_emisor")
    prov = p_data.get("razon_social")
    letra = p_data.get("letra")
    pv = p_data.get("punto_venta")
    num = p_data.get("numero_comprobante")
    tot = p_data.get("total")
    cae = p_data.get("cae")
    oc = p_data.get("orden_compra")
    est = p_data.get("estado")

    print(f"[{idx:02d}] {rel}")
    if p_data:
        print(f"     PROGRAMA: CUIT={cuit} | Prov='{prov}' | Comp={letra} {pv}-{num} | Total={tot} | CAE={cae} | OC={oc} | Estado={est}")
    else:
        print(f"     PROGRAMA DESCARTO: {msg}")
    if incongruencias:
        print(f"     DISCREPANCIAS: {incongruencias}")
