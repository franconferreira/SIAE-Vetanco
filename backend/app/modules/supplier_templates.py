"""
Catálogo de Plantillas y Few-Shot Hints para los 20 Proveedores Recurrentes de Vetanco S.A.
[RF-07] Guía al motor LLM / extractor en la ubicación de tablas, Orden de Compra y desglose impositivo.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models import Proveedor
from app.modules.validators import limpiar_cuit

PROVEEDORES_RECURRENTES: List[Dict[str, Any]] = [
    {
        "cuit": "30708912014",
        "razon_social": "QUIMICA VETERINARIA ARGENTINA S.A.",
        "codigo_acreedor_sap": "PROV_30708912014",
        "planta_default": "PL01",
        "contacto_email": "ventas@quimicavet.com.ar",
        "few_shot_hint": "La Orden de Compra figura en el campo 'Observaciones' o 'Orden de Pedido' con formato '45000xxxxx'. Desglosa IIBB Buenos Aires (alícuota 3.5%). Insumos: Principios activos (Ivermectina, Oxitetraciclina)."
    },
    {
        "cuit": "30708912022",
        "razon_social": "BIOGENESIS INSUMOS FARMA S.R.L.",
        "codigo_acreedor_sap": "PROV_30708912022",
        "planta_default": "PL01",
        "contacto_email": "facturacion@biogenesis-insumos.com",
        "few_shot_hint": "El número de OC se detalla al pie de la tabla de ítems. Suele facturar con IVA 21% y percepción IIBB CABA. Insumos: Excipientes biológicos y adyuvantes inmunológicos."
    },
    {
        "cuit": "30708912030",
        "razon_social": "DROGUERIA AGROVET INDUSTRIAL S.A.",
        "codigo_acreedor_sap": "PROV_30708912030",
        "planta_default": "PL02",
        "contacto_email": "comercial@agrovet.com.ar",
        "few_shot_hint": "Ubicación de OC en cabecera derecha como 'Ref. Cliente / OC'. Emite comprobantes con alícuotas mixtas (21% y 10.5%). Insumos: Antibióticos (Amoxicilina Trihidrato, Cefalexina)."
    },
    {
        "cuit": "30708912049",
        "razon_social": "ENVASES FARMACEUTICOS DEL SUR S.A.",
        "codigo_acreedor_sap": "PROV_30708912049",
        "planta_default": "PL01",
        "contacto_email": "administracion@envasesfarmadelsur.com",
        "few_shot_hint": "La OC figura en el cuerpo bajo 'Pedido de Compra'. Facturas típicamente gravadas al 21% de IVA sin percepciones. Insumos: Frascos ampolla vidrio tipo II, tapones de bromobutilo y sellos de aluminio."
    },
    {
        "cuit": "30708912057",
        "razon_social": "LABORATORIOS APOLO MATERIAS PRIMAS S.A.",
        "codigo_acreedor_sap": "PROV_30708912057",
        "planta_default": "PL01",
        "contacto_email": "cobranzas@apolo-mp.com",
        "few_shot_hint": "OC referenciada en esquina superior izquierda. Incluye siempre desglose de Percepción IVA (RG 2408). Insumos: Vitaminas hidrosolubles y complejos minerales inyectables."
    },
    {
        "cuit": "30708912065",
        "razon_social": "DISTRIBUIDORA BIOQUIMICA CENTRAL S.A.",
        "codigo_acreedor_sap": "PROV_30708912065",
        "planta_default": "PL02",
        "contacto_email": "cuentas@bioquimicacentral.com",
        "few_shot_hint": "OC en campo 'Nro. de Remito / OC'. Tabla con códigos internos de proveedor en columna 1. Insumos: Enrofloxacina base y Flunixin Meglumina."
    },
    {
        "cuit": "30708912073",
        "razon_social": "SINTESIS QUIMICA INDUSTRIAL S.A.",
        "codigo_acreedor_sap": "PROV_30708912073",
        "planta_default": "PL01",
        "contacto_email": "ventas@sintesisquimica.com.ar",
        "few_shot_hint": "Factura electrónica con código de barras en el pie. OC consignada como 'O.C. N°'. Insumos: Solventes grado farmacéutico (Propilenglicol, Alcohol Bencílico)."
    },
    {
        "cuit": "30708912081",
        "razon_social": "VET-PHARMA INTERNACIONAL S.A.",
        "codigo_acreedor_sap": "PROV_30708912081",
        "planta_default": "PL02",
        "contacto_email": "ar-invoicing@vetpharmaglobal.com",
        "few_shot_hint": "Facturación frecuente en moneda extranjera (USD) con cotización BNA vendedora. OC en texto de cabecera. Insumos: Antiparasitarios (Albendazol, Fenbendazol)."
    },
    {
        "cuit": "30708912099",
        "razon_social": "IMPORTADORA DE PRINCIPIOS ACTIVOS S.R.L.",
        "codigo_acreedor_sap": "PROV_30708912099",
        "planta_default": "PL01",
        "contacto_email": "comercioexterior@principiosactivos.com",
        "few_shot_hint": "OC en observaciones. Ítems detallados en kilogramos (KG) o toneladas (TN). Percepción IIBB Provincia de Buenos Aires. Insumos: Doxiciclina Hiclato y Tilosina Tartrato."
    },
    {
        "cuit": "30708912103",
        "razon_social": "POLIMEROS Y ENVASES SAN MARTIN S.A.",
        "codigo_acreedor_sap": "PROV_30708912103",
        "planta_default": "PL02",
        "contacto_email": "facturas@polimerossanmartin.com.ar",
        "few_shot_hint": "OC bajo el título 'Orden de Compra Cliente'. Factura A estándar IVA 21%. Insumos: Bidones PEAD 5L y 20L para antiparasitarios orales."
    },
    {
        "cuit": "30708912111",
        "razon_social": "AGROQUIMICA DEL LITORAL S.A.",
        "codigo_acreedor_sap": "PROV_30708912111",
        "planta_default": "PL01",
        "contacto_email": "administracion@agroquimicalitoral.com",
        "few_shot_hint": "OC en el detalle de cada línea de ítem. Alícuota reducida IVA 10.5% en productos agropecuarios específicos. Insumos: Aditivos nutricionales y acidificantes."
    },
    {
        "cuit": "30708912129",
        "razon_social": "BIOINSPECTION & CONTROLS S.R.L.",
        "codigo_acreedor_sap": "PROV_30708912129",
        "planta_default": "PL02",
        "contacto_email": "servicios@bioinspection.com",
        "few_shot_hint": "OC en cabecera 'Orden de Servicio / Pedido'. Factura por servicios de control analítico y reactivos de control microbiológico."
    },
    {
        "cuit": "30708912138",
        "razon_social": "FRACCIONADORA VETERINARIA PAMPEANA S.A.",
        "codigo_acreedor_sap": "PROV_30708912138",
        "planta_default": "PL01",
        "contacto_email": "ventas@vetpampeana.com.ar",
        "few_shot_hint": "OC al pie de página. Gran detalle de números de lote en las descripciones de los insumos. Insumos: Harina de soya micronizada y carbonato de calcio precipitado."
    },
    {
        "cuit": "30708912146",
        "razon_social": "SOLUCIONES TERAPEUTICAS ANIMALES S.A.",
        "codigo_acreedor_sap": "PROV_30708912146",
        "planta_default": "PL02",
        "contacto_email": "finanzas@solucionesterapeuticas.com",
        "few_shot_hint": "OC al pie como 'Pedido Vetanco'. Desglosa percepciones IIBB Santa Fe y Buenos Aires. Insumos: Antiinflamatorios no esteroideos (Meloxicam, Ketoprofeno)."
    },
    {
        "cuit": "30708912154",
        "razon_social": "VITAMINAS Y MINERALES NUTRICION S.A.",
        "codigo_acreedor_sap": "PROV_30708912154",
        "planta_default": "PL01",
        "contacto_email": "cuentas@vitaminsnutricion.com.ar",
        "few_shot_hint": "OC en campo de texto 'Datos Adicionales'. Facturas con múltiples alícuotas impositivas. Insumos: Vitamina A Palmitato, Vitamina E 50% y Selenito de Sodio."
    },
    {
        "cuit": "30708912162",
        "razon_social": "EXCIPIENTES ARGENTINA S.R.L.",
        "codigo_acreedor_sap": "PROV_30708912162",
        "planta_default": "PL02",
        "contacto_email": "info@excipientesargentina.com",
        "few_shot_hint": "OC en el margen derecho. Cantidades en kilogramos. Insumos: Almidón de maíz pregelatinizado, Celulosa microcristalina y Estearato de magnesio."
    },
    {
        "cuit": "30708912170",
        "razon_social": "MICROBIOLOGIA VETERINARIA APLICADA S.A.",
        "codigo_acreedor_sap": "PROV_30708912170",
        "planta_default": "PL01",
        "contacto_email": "cobranzas@microvetaplicada.com",
        "few_shot_hint": "OC en encabezado de comprobante. Alícuota 21% general. Insumos: Medios de cultivo bacteriológico, peptonas y extracto de levadura."
    },
    {
        "cuit": "30708912189",
        "razon_social": "ANTIBIOTICOS Y DERIVADOS QUIMICOS S.A.",
        "codigo_acreedor_sap": "PROV_30708912189",
        "planta_default": "PL02",
        "contacto_email": "ventas@antibioticosquimicos.com.ar",
        "few_shot_hint": "OC en campo 'Orden de Compra / P.O.'. Suele incluir percepciones impositivas de varias jurisdicciones. Insumos: Sulfadiazina y Trimetoprima."
    },
    {
        "cuit": "30708912197",
        "razon_social": "EMBALAJES TECNICOS HOSPITALARIOS S.R.L.",
        "codigo_acreedor_sap": "PROV_30708912197",
        "planta_default": "PL01",
        "contacto_email": "pedidos@embalajestecnicos.com",
        "few_shot_hint": "OC referenciada en la línea superior de la factura. Insumos: Cajas colectivas de cartón corrugado homologado SENASA y etiquetas de seguridad inviolables."
    },
    {
        "cuit": "30708912200",
        "razon_social": "LOGISTICA E INSUMOS FARMACOS S.A.",
        "codigo_acreedor_sap": "PROV_30708912200",
        "planta_default": "PL02",
        "contacto_email": "facturas@logisticainsumos.com",
        "few_shot_hint": "OC consignada en la cabecera. Facturas por insumos auxiliares de cadena de frío y geles refrigerantes."
    }
]


def sembrar_proveedores_en_bd(db: Session) -> int:
    """Inserta o actualiza los 20 proveedores recurrentes en la tabla 'proveedores' de Staging."""
    insertados = 0
    for data in PROVEEDORES_RECURRENTES:
        cuit_limpio = limpiar_cuit(data["cuit"])
        prov = db.query(Proveedor).filter(Proveedor.cuit == cuit_limpio).first()
        if not prov:
            prov = Proveedor(
                cuit=cuit_limpio,
                razon_social=data["razon_social"],
                codigo_acreedor_sap=data["codigo_acreedor_sap"],
                planta_default=data["planta_default"],
                contacto_email=data.get("contacto_email"),
                guia_extraccion=data["few_shot_hint"]
            )
            db.add(prov)
            insertados += 1
        else:
            # Actualizar guía o datos
            prov.guia_extraccion = data["few_shot_hint"]
            prov.codigo_acreedor_sap = data["codigo_acreedor_sap"]
    db.commit()
    return insertados


def buscar_plantilla_por_cuit_o_texto(texto_pdf: str, cuit_sugerido: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    [RF-07] Busca si el comprobante corresponde a uno de los 20 proveedores recurrentes de Vetanco.
    Retorna la plantilla y el few-shot hint para inyectar en el prompt de Gemini.
    """
    if cuit_sugerido:
        cuit_buscado = limpiar_cuit(cuit_sugerido)
        for prov in PROVEEDORES_RECURRENTES:
            if limpiar_cuit(prov["cuit"]) == cuit_buscado:
                return prov

    # Búsqueda en el texto del PDF
    texto_upper = texto_pdf.upper()
    for prov in PROVEEDORES_RECURRENTES:
        cuit_limpio = limpiar_cuit(prov["cuit"])
        if cuit_limpio in texto_pdf or prov["razon_social"].upper() in texto_upper:
            return prov

    return None
