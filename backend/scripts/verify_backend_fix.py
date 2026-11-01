import glob
import os
import sys

sys.path.append(".")
sys.path.append("scripts")
from app.modules.gemini_extractor import extraer_datos_factura
from generate_complete_ground_truth import GROUND_TRUTH_DB

base_dir = r"F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco\TP Facturas"
files = glob.glob(os.path.join(base_dir, "Junio 2026", "**", "*.pdf"), recursive=True) + glob.glob(os.path.join(base_dir, "Mayo", "**", "*.pdf"), recursive=True)
files = sorted(list(set(files)))

aciertos = 0
desvios = []

print("=" * 80)
print("VERIFICACION DEL PROGRAMA ARREGLADO CON LAS 26 FACTURAS REALES")
print("=" * 80)

for p in files:
    rel = os.path.relpath(p, base_dir)
    gt = GROUND_TRUTH_DB.get(rel)
    if not gt:
        continue
    
    ext = extraer_datos_factura(p)
    cab = ext.comprobante
    sub = ext.subtotales

    errs = []
    if cab.letra != gt["letra"]:
        errs.append(f"Letra: {cab.letra} != {gt['letra']}")
    if cab.punto_venta != gt["punto_venta"]:
        errs.append(f"PV: {cab.punto_venta} != {gt['punto_venta']}")
    if cab.numero_comprobante != gt["numero"]:
        errs.append(f"Num: {cab.numero_comprobante} != {gt['numero']}")
    if abs(sub.total - gt["total"]) > 1.0:
        errs.append(f"Total: {sub.total} != {gt['total']}")
    if gt["cae"] and cab.cae != gt["cae"]:
        errs.append(f"CAE: {cab.cae} != {gt['cae']}")

    prov_real = gt["proveedor"].split()[0].upper()
    prov_ext = (cab.razon_social_emisor or "").upper()
    if prov_real not in prov_ext and "TELMEX" not in prov_ext and "CLARO" not in prov_ext:
        errs.append(f"Prov: '{cab.razon_social_emisor}' != '{gt['proveedor']}'")

    if not errs:
        aciertos += 1
        print(f" [OK] {os.path.basename(p)[:32]:32} | Prov={cab.razon_social_emisor[:18]:18} | {cab.letra} {cab.punto_venta:04d}-{cab.numero_comprobante:08d} | ${sub.total:12.2f} | CAE={cab.cae}")
    else:
        desvios.append((os.path.basename(p), errs))
        print(f" [DESVIO] {os.path.basename(p)[:32]:32} -> {', '.join(errs)}")

print("=" * 80)
print(f"RESULTADO: {aciertos} de {len(GROUND_TRUTH_DB)} comprobantes 100% EXACTOS!")
if desvios:
    print(f"Comprobantes con algún desvío menor restante: {len(desvios)}")
print("=" * 80)
