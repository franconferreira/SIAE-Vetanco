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

prog_by_file = {}
for r in reporte:
    prog_by_file[os.path.normpath(r["archivo"])] = r

GROUND_TRUTH_DB = {
    "Junio 2026\\23202071759_011_00001_00000101.pdf": {
        "proveedor": "RODRIGUEZ EDUARDO EMILIO",
        "cuit_emisor": "23202071759",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 1,
        "numero": 101,
        "fecha": "2026-05-31",
        "cae": "86227756810275",
        "vto_cae": "2026-06-10",
        "moneda": "ARS",
        "total": 1225000.0,
        "orden_compra": None,
        "categoria": "Monotributo / Servicios Profesionales"
    },
    "Junio 2026\\27221638803_011_00001_00000212.pdf": {
        "proveedor": "CARRACEDO LORENA",
        "cuit_emisor": "27221638803",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 1,
        "numero": 212,
        "fecha": "2026-05-31",
        "cae": "86228013195141",
        "vto_cae": "2026-06-10",
        "moneda": "ARS",
        "total": 350000.0,
        "orden_compra": None,
        "categoria": "Monotributo / Servicios Profesionales"
    },
    "Junio 2026\\A05-0535.pdf": {
        "proveedor": "NEWAY IT S.R.L.",
        "cuit_emisor": "30714160180",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 5,
        "numero": 535,
        "fecha": "2026-05-31",
        "cae": "86227825574193",
        "vto_cae": "2026-06-11",
        "moneda": "ARS",
        "total": 78214.40,
        "orden_compra": None,
        "categoria": "Servicios IT"
    },
    "Junio 2026\\BOSIO FC 121.pdf": {
        "proveedor": "BOSIO RODRIGO SEBASTIAN",
        "cuit_emisor": "20239926968",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 3,
        "numero": 181,
        "fecha": "2026-05-20",
        "cae": "86206368747213",
        "vto_cae": "2026-05-30",
        "moneda": "ARS",
        "total": 1645000.0,
        "orden_compra": None,
        "categoria": "Honorarios Profesionales"
    },
    "Junio 2026\\CLARO FC 00357765.pdf": {
        "proveedor": "TELMEX ARGENTINA S.A. (CLARO)",
        "cuit_emisor": "33695098419",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 70,
        "numero": 357765,
        "fecha": "2026-05-06",
        "cae": None,
        "vto_cae": None,
        "moneda": "ARS",
        "total": 1246762.86,
        "orden_compra": None,
        "categoria": "Telecomunicaciones / Enlaces"
    },
    "Junio 2026\\CLARO FC 0070A00362809.pdf": {
        "proveedor": "TELMEX ARGENTINA S.A. (CLARO)",
        "cuit_emisor": "33695098419",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 70,
        "numero": 362809,
        "fecha": "2026-06-04",
        "cae": None,
        "vto_cae": None,
        "moneda": "ARS",
        "total": 1292772.77,
        "orden_compra": None,
        "categoria": "Telecomunicaciones / Enlaces"
    },
    "Junio 2026\\DATACLOUD FC 1646.pdf": {
        "proveedor": "DATACLOUD S.A.",
        "cuit_emisor": "30717164322",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 1646,
        "fecha": "2026-05-05",
        "cae": "86184226366859",
        "vto_cae": "2026-05-15",
        "moneda": "USD",
        "total": 481.58,
        "orden_compra": "CARTA DE ACEPTACION",
        "categoria": "Servicios Cloud / Hosting"
    },
    "Junio 2026\\EVEREST FC 1201.pdf": {
        "proveedor": "EVEREST TECHNOLOGIES S.R.L.",
        "cuit_emisor": "30710234929",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 12019,
        "fecha": "2026-06-01",
        "cae": "86227828347890",
        "vto_cae": "2026-06-11",
        "moneda": "ARS",
        "total": 317621.37,
        "orden_compra": None,
        "categoria": "Mantenimiento InfoBroker"
    },
    "Junio 2026\\FA-A 00002-00004640.pdf": {
        "proveedor": "ARQUETIPONET S.R.L. (CUBE)",
        "cuit_emisor": "30711751994",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 2,
        "numero": 4640,
        "fecha": "2026-06-01",
        "cae": "86227908845546",
        "vto_cae": "2026-06-11",
        "moneda": "ARS",
        "total": 405088.34,
        "orden_compra": None,
        "categoria": "Servicios Conectividad"
    },
    "Junio 2026\\FACTURA_N_0001-00001702 VETANCO.pdf": {
        "proveedor": "DATACLOUD S.A.",
        "cuit_emisor": "30717164322",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 1702,
        "fecha": "2026-06-02",
        "cae": "86228025448820",
        "vto_cae": "2026-06-12",
        "moneda": "USD",
        "total": 481.58,
        "orden_compra": "CARTA DE ACEPTACION",
        "categoria": "Servicios Cloud / Hosting"
    },
    "Junio 2026\\FC_GUSTAVO A. I. PANZITTA_202605.pdf": {
        "proveedor": "PANZITTA GUSTAVO ANDRES IGNACIO",
        "cuit_emisor": "23260469029",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 5,
        "numero": 29,
        "fecha": "2026-05-27",
        "cae": "86227242495413",
        "vto_cae": "2026-06-06",
        "moneda": "ARS",
        "total": 2450000.0,
        "orden_compra": None,
        "categoria": "Honorarios Profesionales"
    },
    "Junio 2026\\GS1_FC C-00007-00035061.pdf": {
        "proveedor": "GS1 ARGENTINA",
        "cuit_emisor": "30656017631",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 7,
        "numero": 35061,
        "fecha": "2026-05-08",
        "cae": "86194739867474",
        "vto_cae": "2026-05-08",
        "moneda": "ARS",
        "total": 621500.0,
        "orden_compra": None,
        "categoria": "Códigos de Barra / GS1"
    },
    "Junio 2026\\MORENO FC 23.pdf": {
        "proveedor": "MORENO YANINA ANDREA",
        "cuit_emisor": "27337100231",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 1,
        "numero": 23,
        "fecha": "2026-06-04",
        "cae": "86238642220842",
        "vto_cae": "2026-06-14",
        "moneda": "ARS",
        "total": 1190000.0,
        "orden_compra": None,
        "categoria": "Servicios Profesionales"
    },
    "Junio 2026\\NETLATIN FC 00018832.pdf": {
        "proveedor": "NETLATIN S.R.L.",
        "cuit_emisor": "30715868926",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 18832,
        "fecha": "2026-06-01",
        "cae": "86227279847261",
        "vto_cae": "2026-06-11",
        "moneda": "USD",
        "total": 484.0,
        "orden_compra": None,
        "categoria": "Internet Industrial"
    },
    "Junio 2026\\No corrresponde\\Factura de Venta A N° 0003-00030403.pdf": {
        "proveedor": "AUDITECOM SRL",
        "cuit_emisor": "30715261142",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 3,
        "numero": 30403,
        "fecha": "2026-05-22",
        "cae": "86216574958302",
        "vto_cae": "2026-06-01",
        "moneda": "ARS",
        "total": 588857.39,
        "orden_compra": None,
        "categoria": "Auditoría Médica / Ocupacional"
    },
    "Junio 2026\\No corrresponde\\Factura de Venta A N° 0003-00030404.pdf": {
        "proveedor": "AUDITECOM SRL",
        "cuit_emisor": "30715261142",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 3,
        "numero": 30404,
        "fecha": "2026-05-22",
        "cae": "86216575125525",
        "vto_cae": "2026-06-01",
        "moneda": "ARS",
        "total": 588857.39,
        "orden_compra": None,
        "categoria": "Auditoría Médica / Ocupacional"
    },
    "Junio 2026\\No corrresponde\\Factura de Venta N° A-00003-00005916.pdf": {
        "proveedor": "PATH COMUNICACION S.R.L.",
        "cuit_emisor": "30709280690",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 3,
        "numero": 5916,
        "fecha": "2026-05-31",
        "cae": "86238944111944",
        "vto_cae": "2026-06-15",
        "moneda": "ARS",
        "total": 314600.0,
        "orden_compra": None,
        "categoria": "Comunicación Institucional"
    },
    "Mayo\\20239926968_011_00003_00000180.pdf": {
        "proveedor": "BOSIO RODRIGO SEBASTIAN",
        "cuit_emisor": "20239926968",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 3,
        "numero": 180,
        "fecha": "2026-04-24",
        "cae": "86173217943085",
        "vto_cae": "2026-05-04",
        "moneda": "ARS",
        "total": 1770000.0,
        "orden_compra": None,
        "categoria": "Honorarios Profesionales"
    },
    "Mayo\\27221638803_011_00001_00000210.pdf": {
        "proveedor": "CARRACEDO LORENA",
        "cuit_emisor": "27221638803",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 1,
        "numero": 210,
        "fecha": "2026-05-04",
        "cae": "86184170241107",
        "vto_cae": "2026-05-14",
        "moneda": "ARS",
        "total": 490000.0,
        "orden_compra": None,
        "categoria": "Servicios Profesionales"
    },
    "Mayo\\A05-0520.pdf": {
        "proveedor": "NEWAY IT S.R.L.",
        "cuit_emisor": "30714160180",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 5,
        "numero": 520,
        "fecha": "2026-04-30",
        "cae": "86184044820796",
        "vto_cae": "2026-05-14",
        "moneda": "ARS",
        "total": 78214.40,
        "orden_compra": None,
        "categoria": "Servicios IT"
    },
    "Mayo\\Comprobante_01_0001_00018508.pdf": {
        "proveedor": "NETLATIN S.R.L.",
        "cuit_emisor": "30715868926",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 18508,
        "fecha": "2026-05-01",
        "cae": "86173144473443",
        "vto_cae": "2026-05-11",
        "moneda": "USD",
        "total": 484.0,
        "orden_compra": None,
        "categoria": "Internet Industrial"
    },
    "Mayo\\FA-A 00002-00004596.pdf": {
        "proveedor": "ARQUETIPONET S.R.L. (CUBE)",
        "cuit_emisor": "30711751994",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 2,
        "numero": 4596,
        "fecha": "2026-05-01",
        "cae": "86183777003300",
        "vto_cae": "2026-05-11",
        "moneda": "ARS",
        "total": 405088.34,
        "orden_compra": None,
        "categoria": "Servicios Conectividad"
    },
    "Mayo\\FACTURA 0001-00011917A.PDF": {
        "proveedor": "EVEREST TECHNOLOGIES S.R.L.",
        "cuit_emisor": "30710234929",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 1,
        "numero": 11917,
        "fecha": "2026-05-04",
        "cae": "86184114205705",
        "vto_cae": "2026-05-14",
        "moneda": "ARS",
        "total": 309572.45,
        "orden_compra": None,
        "categoria": "Mantenimiento InfoBroker"
    },
    "Mayo\\FC_GUSTAVO A. I. PANZITTA_202604.pdf": {
        "proveedor": "PANZITTA GUSTAVO ANDRES IGNACIO",
        "cuit_emisor": "23260469029",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 5,
        "numero": 28,
        "fecha": "2026-04-28",
        "cae": "86173261923588",
        "vto_cae": "2026-05-08",
        "moneda": "ARS",
        "total": 2450000.0,
        "orden_compra": None,
        "categoria": "Honorarios Profesionales"
    },
    "Mayo\\Factura Electrónica 0006-00017606.PDF": {
        "proveedor": "SEIDOR TECHNOLOGIES S.A.",
        "cuit_emisor": "30707970428",
        "cuit_receptor": "30623368935",
        "letra": "A",
        "punto_venta": 6,
        "numero": 17606,
        "fecha": "2026-05-04",
        "cae": "86184101276589",
        "vto_cae": "2026-05-14",
        "moneda": "ARS",
        "total": 442785.03,
        "orden_compra": "4700092156",
        "categoria": "Consultoría SAP"
    },
    "Mayo\\_00001_00000099 rodriguez.pdf": {
        "proveedor": "RODRIGUEZ EDUARDO EMILIO",
        "cuit_emisor": "23202071759",
        "cuit_receptor": "30623368935",
        "letra": "C",
        "punto_venta": 1,
        "numero": 99,
        "fecha": "2026-05-02",
        "cae": "86183936798502",
        "vto_cae": "2026-05-12",
        "moneda": "ARS",
        "total": 1365000.0,
        "orden_compra": None,
        "categoria": "Servicios Profesionales"
    }
}

print(f"Total en DB Ground Truth: {len(GROUND_TRUTH_DB)}")
discrepancias_totales = []

for rel_path, gt in GROUND_TRUTH_DB.items():
    norm = os.path.normpath(rel_path)
    prog_entry = prog_by_file.get(norm, {})
    p_data = prog_entry.get("programa", {})
    msg = prog_entry.get("mensaje_ingesta", "")

    fallos_archivo = []

    if not p_data:
        fallos_archivo.append(f"DESCARTE TOTAL: {msg}")
    else:
        # Comparar CUIT
        if str(p_data.get("cuit_emisor")) != str(gt["cuit_emisor"]):
            fallos_archivo.append(f"CUIT emisor: Programa={p_data.get('cuit_emisor')} vs Real={gt['cuit_emisor']}")

        # Comparar Proveedor
        prov_prog = (p_data.get("razon_social") or "").upper()
        palabra_clave = gt["proveedor"].split()[0].upper()
        if palabra_clave not in prov_prog and "TELMEX" not in prov_prog and "CLARO" not in prov_prog:
            fallos_archivo.append(f"Proveedor: Programa='{p_data.get('razon_social')}' vs Real='{gt['proveedor']}'")

        # Comparar Comprobante (Letra, Punto Venta, Numero)
        if p_data.get("letra") != gt["letra"]:
            fallos_archivo.append(f"Letra: Programa={p_data.get('letra')} vs Real={gt['letra']}")
        if int(p_data.get("punto_venta") or 0) != int(gt["punto_venta"]):
            fallos_archivo.append(f"Punto de Venta: Programa={p_data.get('punto_venta')} vs Real={gt['punto_venta']}")
        if int(p_data.get("numero_comprobante") or 0) != int(gt["numero"]):
            fallos_archivo.append(f"Número de Comprobante: Programa={p_data.get('numero_comprobante')} vs Real={gt['numero']}")

        # Comparar Total
        tot_prog = float(p_data.get("total") or 0)
        tot_real = float(gt["total"])
        if abs(tot_prog - tot_real) > 1.0:
            fallos_archivo.append(f"Total facturado: Programa={tot_prog} vs Real={tot_real} ({gt['moneda']})")

        # Comparar CAE
        cae_prog = str(p_data.get("cae") or "").strip()
        cae_real = str(gt["cae"] or "").strip()
        if cae_real and cae_real != cae_prog:
            fallos_archivo.append(f"CAE: Programa={cae_prog or 'None'} vs Real={cae_real}")

        # Comparar OC
        oc_prog = str(p_data.get("orden_compra") or "").strip()
        oc_real = str(gt["orden_compra"] or "").strip()
        if oc_real and oc_real != "None" and oc_prog != oc_real:
            fallos_archivo.append(f"Orden de Compra: Programa={oc_prog or 'None'} vs Real={oc_real}")

    if fallos_archivo:
        discrepancias_totales.append({
            "archivo": rel_path,
            "ground_truth": gt,
            "programa": p_data,
            "fallos": fallos_archivo
        })

print(f"\n==========================================")
print(f"RESULTADO DEL CRUCE GROUND TRUTH VS PROGRAMA:")
print(f"Facturas analizadas: {len(GROUND_TRUTH_DB)}")
print(f"Facturas con discrepancias de extraccion: {len(discrepancias_totales)}")
print(f"Facturas 100% exactas: {len(GROUND_TRUTH_DB) - len(discrepancias_totales)}")
print(f"==========================================\n")

for d in discrepancias_totales:
    print(f"-> {d['archivo']}")
    for f in d['fallos']:
        print(f"   [!] {f}")

with open("data/informe_incongruencias_definitivo.json", "w", encoding="utf-8") as f:
    json.dump(discrepancias_totales, f, indent=2, ensure_ascii=False)
