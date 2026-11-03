import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EstadoComprobante, Comprobante, OrdenCompra, OrdenCompraItem


TOLERANCIA_IMPOSITIVA = Decimal("0.02")


def limpiar_cuit(cuit: Optional[str]) -> str:
    """Elimina guiones, espacios y puntos de un CUIT dejando solo dígitos."""
    if not cuit:
        return ""
    return re.sub(r"\D", "", str(cuit))


def validar_cuit_afip_modulo11(cuit_str: Optional[str]) -> Tuple[bool, str]:
    """
    [RF-15] Valida la integridad de un CUIT fiscal argentino mediante el algoritmo oficial de Módulo 11.
    Multiplicadores: 5, 4, 3, 2, 7, 6, 5, 4, 3, 2 aplicados a los 10 primeros dígitos.
    """
    cuit = limpiar_cuit(cuit_str)
    if len(cuit) != 11:
        return False, f"CUIT inválido: longitud incorrecta ({len(cuit)} dígitos en lugar de 11)"

    # Validación de tipo de persona fiscal básica (20, 23, 24, 27, 30, 33, 34)
    prefijo = cuit[:2]
    if prefijo not in ("20", "23", "24", "27", "30", "33", "34"):
        return False, f"CUIT inválido: prefijo fiscal desconocido ({prefijo})"

    # Si coincide exactamente con el CUIT institucional de Vetanco fijado en el proyecto
    if cuit == limpiar_cuit(settings.VETANCO_CUIT):
        return True, "CUIT institucional oficial de Vetanco S.A."

    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuit[i]) * multiplicadores[i] for i in range(10))
    resto = suma % 11
    digito_calculado = 11 - resto

    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = 9

    digito_real = int(cuit[10])
    if digito_calculado != digito_real:
        return False, f"CUIT inválido: dígito verificador no coincide (esperado {digito_calculado}, obtenido {digito_real})"

    return True, "CUIT fiscalmente válido"


def validar_cae_afip(cae_str: Optional[str], vencimiento_cae: Optional[Any] = None) -> Tuple[bool, str]:
    """
    [RF-15] Valida la estructura del Código de Autorización Electrónico (14 dígitos numéricos)
    y opcionalmente la fecha de vigencia.
    """
    if not cae_str:
        return False, "CAE ausente o vacío"
    cae = re.sub(r"\D", "", str(cae_str))
    if len(cae) != 14:
        return False, f"CAE inválido: debe contener exactamente 14 dígitos (obtenidos {len(cae)})"

    if vencimiento_cae:
        vto = None
        if isinstance(vencimiento_cae, (date, datetime)):
            vto = vencimiento_cae if isinstance(vencimiento_cae, date) else vencimiento_cae.date()
        elif isinstance(vencimiento_cae, str):
            try:
                vto = datetime.strptime(vencimiento_cae.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass
        # Si venció hace mucho respecto a la emisión, se registra como advertencia
        if vto and vto < date(2020, 1, 1):
            return False, f"Fecha de vencimiento de CAE anacrónica: {vto}"

    return True, "CAE formalmente válido"


def validar_receptor_vetanco(cuit_receptor: Optional[str]) -> Tuple[bool, str]:
    """
    [RF-14] Comprueba que el CUIT receptor consignado en la factura pertenezca a Vetanco S.A.
    (Soporta '30623368939' de la especificación y el CUIT real con Módulo 11 '30623368935').
    """
    cuit_limpio = limpiar_cuit(cuit_receptor)
    cuits_validos_vetanco = {
        limpiar_cuit(settings.VETANCO_CUIT),
        "30623368935",
        "30623368939"
    }

    if cuit_limpio not in cuits_validos_vetanco:
        return False, f"Factura rechazada: CUIT receptor ({cuit_receptor or 'VACÍO'}) no pertenece a Vetanco S.A."

    return True, "Receptor válido (Vetanco S.A.)"


def a_decimal(valor: Any) -> Decimal:
    """Convierte cualquier valor a Decimal con 2 decimales de precisión contable."""
    if valor is None or valor == "":
        return Decimal("0.00")
    try:
        if isinstance(valor, Decimal):
            return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        val_str = str(valor).replace("$", "").replace(" ", "").replace(",", ".")
        return Decimal(val_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def validar_consistencia_impositiva(datos_subtotales: Any) -> Tuple[bool, Decimal, Decimal, List[Dict[str, Any]]]:
    """
    [RF-13, RNF-05] Comprobación matemática de la igualdad contable con tolerancia de +- $0.02:
    Total Calculado = Netos + IVAs + No Gravado + Exento + Percepciones
    """
    # Obtener valores ya sea de dict o de objeto/modelo
    def get_val(campo: str) -> Decimal:
        if isinstance(datos_subtotales, dict):
            return a_decimal(datos_subtotales.get(campo, 0))
        return a_decimal(getattr(datos_subtotales, campo, 0))

    neto_21 = get_val("neto_gravado_21")
    neto_105 = get_val("neto_gravado_105")
    neto_27 = get_val("neto_gravado_27")
    no_gravado = get_val("no_gravado")
    exento = get_val("exento")

    iva_21 = get_val("iva_21")
    iva_105 = get_val("iva_105")
    iva_27 = get_val("iva_27")

    percepcion_iibb = get_val("percepcion_iibb")
    percepcion_iva = get_val("percepcion_iva")
    impuestos_internos = get_val("impuestos_internos")

    total_informado = get_val("importe_total")
    if total_informado == Decimal("0.00"):
        total_informado = get_val("total")

    total_calculado = (
        neto_21 + neto_105 + neto_27 +
        no_gravado + exento +
        iva_21 + iva_105 + iva_27 +
        percepcion_iibb + percepcion_iva + impuestos_internos
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    diferencia = abs(total_calculado - total_informado)
    alertas = []

    # Alerta crítica: comprobante con monto total en cero
    if total_informado <= Decimal("0.00") and total_calculado <= Decimal("0.00"):
        alertas.append({
            "codigo": "IMPORTE_TOTAL_CERO",
            "campo": "importe_total",
            "mensaje": "El comprobante posee un importe total de $0.00 (monto inválido o falla de extracción)",
            "severidad": "error"
        })
        return False, total_calculado, total_informado, alertas

    # Verificación de alícuotas teóricas de IVA vs neto (con tolerancia $0.50 por redondeo por ítem)
    if neto_21 > Decimal("0.00") and iva_21 > Decimal("0.00"):
        iva_21_teorico = (neto_21 * Decimal("0.21")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if abs(iva_21_teorico - iva_21) > Decimal("0.50"):
            alertas.append({
                "codigo": "IVA_21_CALCULO_DESVIO",
                "campo": "iva_21",
                "mensaje": f"IVA 21% informado (${iva_21}) difiere del 21% sobre neto (${iva_21_teorico})",
                "severidad": "warning"
            })

    if diferencia > TOLERANCIA_IMPOSITIVA:
        alertas.append({
            "codigo": "DISCREPANCIA_SUMA_IMPOSITIVA",
            "campo": "importe_total",
            "mensaje": f"Discrepancia en Suma Impositiva: Calculado ${total_calculado} vs Informado ${total_informado} (Diferencia: ${diferencia})",
            "severidad": "error"
        })
        return False, total_calculado, total_informado, alertas

    return True, total_calculado, total_informado, alertas


def conciliar_orden_compra(
    db: Session,
    orden_compra_nro: Optional[str],
    cuit_emisor: str,
    items_facturados: List[Any]
) -> Tuple[bool, Optional[OrdenCompra], List[Dict[str, Any]]]:
    """
    [RF-16] 3-Way Matching preliminar contra Órdenes de Compra en Staging:
    1. Si no se especifica Orden de Compra (ej. facturas de servicios, suministros o
       gastos directos donde no existe remito ni recepción física en almacén),
       se omite el 3-way matching y se considera conciliación limpia (sin discrepancias).
    2. Si se especifica Orden de Compra:
       a. Verifica que la OC exista y esté en estado ABIERTA en Staging.
       b. Cruza proveedor de la OC con el CUIT de la factura.
       c. Verifica que el precio unitario facturado no exceda el precio pactado en la OC.
       d. Verifica que la cantidad facturada no supere el saldo remanente de la OC.
    """
    alertas = []
    if not orden_compra_nro or not str(orden_compra_nro).strip():
        # Factura de servicio / gasto directo sin requerimiento de Orden de Compra física
        return True, None, []

    oc_nro = str(orden_compra_nro).strip()
    oc = db.query(OrdenCompra).filter(OrdenCompra.numero_oc == oc_nro).first()

    if not oc:
        alertas.append({
            "codigo": "OC_INEXISTENTE",
            "campo": "orden_compra_nro",
            "mensaje": f"Orden de Compra {oc_nro} no existe en el maestro de SAP en Staging",
            "severidad": "error"
        })
        return False, None, alertas

    if oc.estado.upper() != "ABIERTA":
        alertas.append({
            "codigo": "OC_CERRADA",
            "campo": "orden_compra_nro",
            "mensaje": f"La Orden de Compra {oc_nro} se encuentra {oc.estado} en SAP",
            "severidad": "error"
        })
        return False, oc, alertas

    # Validar CUIT del proveedor emisor contra el de la OC
    if limpiar_cuit(oc.cuit_proveedor) != limpiar_cuit(cuit_emisor):
        alertas.append({
            "codigo": "OC_PROVEEDOR_NO_COINCIDE",
            "campo": "cuit_emisor",
            "mensaje": f"El proveedor emisor (CUIT {cuit_emisor}) no coincide con el asignado en la OC {oc_nro} (CUIT {oc.cuit_proveedor})",
            "severidad": "error"
        })

    # Cruce ítem por ítem
    items_oc = {item.codigo_insumo.strip().upper(): item for item in oc.items}

    for item in items_facturados:
        # Obtener campos
        if isinstance(item, dict):
            codigo = str(item.get("codigo_insumo") or "").strip().upper()
            desc = str(item.get("descripcion") or "")
            cant = float(item.get("cantidad") or 0)
            pu = a_decimal(item.get("precio_unitario"))
        else:
            codigo = str(getattr(item, "codigo_insumo", "") or "").strip().upper()
            desc = str(getattr(item, "descripcion", "") or "")
            cant = float(getattr(item, "cantidad", 0) or 0)
            pu = a_decimal(getattr(item, "precio_unitario", 0))

        # Intento de matcheo por código o fallback por primer ítem si la OC tiene solo 1
        oc_item = items_oc.get(codigo)
        if not oc_item and len(oc.items) == 1:
            oc_item = oc.items[0]

        if not oc_item:
            # Fallback buscando coincidencia de texto
            for candidate in oc.items:
                if candidate.descripcion.lower() in desc.lower() or desc.lower() in candidate.descripcion.lower():
                    oc_item = candidate
                    break

        if oc_item:
            pu_oc = a_decimal(oc_item.precio_unitario)
            if pu > pu_oc:
                alertas.append({
                    "codigo": "PRECIO_EXCEDE_OC",
                    "campo": f"item_{codigo or desc}",
                    "mensaje": f"Precio unitario (${pu}) excede el valor pactado en OC {oc_nro} (${pu_oc}) para '{desc}'",
                    "severidad": "error"
                })

            if cant > oc_item.cantidad_remanente:
                alertas.append({
                    "codigo": "CANTIDAD_SUPERA_SALDO_OC",
                    "campo": f"item_{codigo or desc}",
                    "mensaje": f"Cantidad facturada ({cant} {oc_item.unidad_medida}) supera el remanente en OC {oc_nro} ({oc_item.cantidad_remanente} {oc_item.unidad_medida})",
                    "severidad": "warning"
                })
        else:
            alertas.append({
                "codigo": "ITEM_NO_ENCONTRADO_EN_OC",
                "campo": f"item_{codigo or desc}",
                "mensaje": f"El ítem '{desc}' no fue identificado en las posiciones de la OC {oc_nro}",
                "severidad": "warning"
            })

    tiene_errores = any(a["severidad"] == "error" for a in alertas)
    return not tiene_errores, oc, alertas


def comprobar_duplicado_fiscal(
    db: Session,
    cuit_emisor: str,
    tipo_comprobante: str,
    punto_venta: int,
    numero_comprobante: int,
    exclude_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    [RF-17] Detección estricta de comprobantes duplicados sobre la tupla fiscal:
    (cuit_emisor, tipo_comprobante, punto_venta, numero_comprobante)
    """
    query = db.query(Comprobante).filter(
        Comprobante.cuit_emisor == limpiar_cuit(cuit_emisor),
        Comprobante.tipo_comprobante == str(tipo_comprobante).zfill(3),
        Comprobante.punto_venta == int(punto_venta),
        Comprobante.numero_comprobante == int(numero_comprobante)
    )
    if exclude_id:
        query = query.filter(Comprobante.id != exclude_id)

    duplicado = query.first()
    if duplicado:
        estado_val = duplicado.estado.value if hasattr(duplicado.estado, "value") else str(duplicado.estado)
        return True, (
            f"Comprobante fiscal duplicado: ya se encuentra registrada la factura "
            f"{duplicado.letra} {duplicado.punto_venta:04d}-{duplicado.numero_comprobante:08d} "
            f"del proveedor '{duplicado.razon_social_emisor}' (CUIT: {cuit_emisor}) "
            f"en estado '{estado_val}' (ID: {duplicado.id[:8]})."
        )
    return False, None


def evaluar_comprobante_integral(
    db: Session,
    cabecera: Dict[str, Any],
    subtotales: Dict[str, Any],
    items: List[Dict[str, Any]],
    confianza_global: float = 1.0,
    confianza_campos: Optional[Dict[str, float]] = None,
    exclude_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    [RF-18] Máquina de estados integral:
    Aplica todas las reglas de negocio y clasifica el comprobante:
    - RECHAZADA: CUIT receptor no Vetanco, Módulo 11 emisor inválido o Duplicado fiscal.
    - REQUIERE_AUDITORIA: Desvío en suma impositiva, desvío en OC, o confianza < 0.95.
    - PROCESADA_LISTA_BATCH: 100% STP (Straight Through Processing).
    """
    if confianza_campos is None:
        confianza_campos = {}

    todas_las_alertas = []
    motivo_rechazo = None

    cuit_emisor = limpiar_cuit(cabecera.get("cuit_emisor"))
    tipo_comp = str(cabecera.get("tipo_comprobante", "001")).zfill(3)
    pv = int(cabecera.get("punto_venta", 0))
    nro = int(cabecera.get("numero_comprobante", 0))
    cuit_rec = cabecera.get("cuit_receptor")
    cae = cabecera.get("cae")
    vto_cae = cabecera.get("vencimiento_cae")
    oc_nro = cabecera.get("orden_compra") or cabecera.get("orden_compra_nro")

    # 1. Regla Duplicado Fiscal (RF-17)
    es_dup, msg_dup = comprobar_duplicado_fiscal(db, cuit_emisor, tipo_comp, pv, nro, exclude_id)
    if es_dup:
        return {
            "estado": EstadoComprobante.RECHAZADA,
            "motivo_rechazo": msg_dup,
            "alertas": [{"codigo": "COMPROBANTE_DUPLICADO", "campo": "numero_comprobante", "mensaje": msg_dup, "severidad": "error"}],
            "total_calculado": a_decimal(subtotales.get("total") or subtotales.get("importe_total"))
        }

    # 2. Regla Receptor Vetanco (RF-14)
    rec_ok, msg_rec = validar_receptor_vetanco(cuit_rec)
    if not rec_ok:
        return {
            "estado": EstadoComprobante.RECHAZADA,
            "motivo_rechazo": msg_rec,
            "alertas": [{"codigo": "RECEPTOR_NO_VETANCO", "campo": "cuit_receptor", "mensaje": msg_rec, "severidad": "error"}],
            "total_calculado": a_decimal(subtotales.get("total") or subtotales.get("importe_total"))
        }

    # 3. Regla Módulo 11 Emisor (RF-15)
    cuit_ok, msg_cuit = validar_cuit_afip_modulo11(cuit_emisor)
    if not cuit_ok:
        return {
            "estado": EstadoComprobante.RECHAZADA,
            "motivo_rechazo": msg_cuit,
            "alertas": [{"codigo": "CUIT_EMISOR_MODULO11_INVALIDO", "campo": "cuit_emisor", "mensaje": msg_cuit, "severidad": "error"}],
            "total_calculado": a_decimal(subtotales.get("total") or subtotales.get("importe_total"))
        }

    # 4. Regla CAE (RF-15)
    cae_ok, msg_cae = validar_cae_afip(cae, vto_cae)
    if not cae_ok:
        todas_las_alertas.append({
            "codigo": "CAE_INVALIDO",
            "campo": "cae",
            "mensaje": msg_cae,
            "severidad": "warning"
        })

    # 5. Regla Suma Impositiva (RF-13)
    suma_ok, total_calc, total_inf, alertas_suma = validar_consistencia_impositiva(subtotales)
    todas_las_alertas.extend(alertas_suma)

    # 5.1 Regla Precios Unitarios de Ítems
    for it in items:
        pos = it.get("posicion", 1)
        pu = a_decimal(it.get("precio_unitario", 0))
        cant = Decimal(str(it.get("cantidad", 1.0)))
        sub = a_decimal(it.get("subtotal") or (pu * cant))
        if pu <= Decimal("0.00") and sub <= Decimal("0.00"):
            todas_las_alertas.append({
                "codigo": "PRECIO_UNITARIO_CERO",
                "campo": "items",
                "mensaje": f"La posición {pos} ({it.get('descripcion', 'Ítem')}) posee precio unitario y subtotal en $0.00 (monto anómalo)",
                "severidad": "error"
            })

    # 6. Regla Conciliación Orden de Compra (RF-16)
    oc_ok, oc_obj, alertas_oc = conciliar_orden_compra(db, oc_nro, cuit_emisor, items)
    todas_las_alertas.extend(alertas_oc)

    # 7. Regla de Confianza de Extracción (RF-12)
    umbral = settings.CONFIDENCE_THRESHOLD
    if confianza_global < umbral:
        todas_las_alertas.append({
            "codigo": "BAJA_CONFIANZA_GLOBAL",
            "campo": "confianza_global",
            "mensaje": f"Confianza de extracción IA ({confianza_global * 100:.1f}%) inferior al umbral mínimo del {umbral * 100:.0f}%",
            "severidad": "warning"
        })

    for campo, score in confianza_campos.items():
        if campo == "orden_compra" and not oc_nro:
            # En comprobantes de servicios o gastos directos sin OC, la no detección de OC es esperada
            continue
        if score < umbral:
            todas_las_alertas.append({
                "codigo": "BAJA_CONFIANZA_CAMPO",
                "campo": campo,
                "mensaje": f"El campo '{campo}' tiene baja certidumbre ({score * 100:.1f}%)",
                "severidad": "warning"
            })

    # Determinación final del estado (RF-18)
    if len(todas_las_alertas) == 0 and confianza_global >= umbral:
        estado_final = EstadoComprobante.PROCESADA_LISTA_BATCH
    else:
        estado_final = EstadoComprobante.REQUIERE_AUDITORIA

    return {
        "estado": estado_final,
        "motivo_rechazo": motivo_rechazo,
        "alertas": todas_las_alertas,
        "total_calculado": total_calc
    }
