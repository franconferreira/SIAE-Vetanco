from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models import EstadoComprobante, TipoDisparoBatch


# =====================================================================
# 1. Esquemas para Extracción Estructurada con Gemini (RF-08 a RF-12)
# =====================================================================

class ItemFacturaExtraido(BaseModel):
    posicion: int = Field(default=1, description="Número de línea / posición en la factura")
    codigo_insumo: Optional[str] = Field(default=None, description="Código de producto o materia prima")
    descripcion: str = Field(description="Denominación del insumo o materia prima")
    cantidad: float = Field(description="Cantidad de unidades o peso")
    unidad_medida: str = Field(default="KG", description="KG, L, UN, TN, etc.")
    precio_unitario: float = Field(description="Precio unitario acordado")
    subtotal: float = Field(description="Subtotal de la línea (cantidad * precio_unitario)")
    alicuota_iva: float = Field(default=21.0, description="Alícuota IVA aplicada (21.0, 10.5, 0.0)")


class CabeceraComprobanteExtraida(BaseModel):
    cuit_emisor: str = Field(description="CUIT del proveedor emisor (11 dígitos sin guiones)")
    razon_social_emisor: str = Field(description="Nombre o razón social del proveedor")
    tipo_comprobante: str = Field(default="001", description="Código numérico AFIP (001: Factura A, 006: Factura B)")
    letra: str = Field(default="A", description="Letra del comprobante: A, B o M")
    punto_venta: int = Field(description="Punto de venta (4 o 5 dígitos)")
    numero_comprobante: int = Field(description="Número de comprobante secuencial (hasta 8 dígitos)")
    fecha_emision: str = Field(description="Fecha de emisión en formato AAAA-MM-DD")
    fecha_vencimiento: Optional[str] = Field(default=None, description="Fecha límite de pago (AAAA-MM-DD)")
    cae: Optional[str] = Field(default=None, description="Código de Autorización Electrónico (14 dígitos AFIP)")
    vencimiento_cae: Optional[str] = Field(default=None, description="Fecha de vencimiento del CAE (AAAA-MM-DD)")
    cuit_receptor: Optional[str] = Field(default="30623368939", description="CUIT receptor consignado")
    orden_compra: Optional[str] = Field(default=None, description="Número de Orden de Compra Vetanco")


class SubtotalesExtraidos(BaseModel):
    moneda: str = Field(default="ARS", description="Código ISO de moneda: ARS, USD")
    tipo_cambio: float = Field(default=1.0, description="Cotización si es moneda extranjera")
    neto_gravado_21: float = Field(default=0.0, description="Base imponible gravada al 21%")
    iva_21: float = Field(default=0.0, description="Importe de IVA liquidado al 21%")
    neto_gravado_105: float = Field(default=0.0, description="Base imponible gravada al 10.5%")
    iva_105: float = Field(default=0.0, description="Importe de IVA liquidado al 10.5%")
    neto_gravado_27: float = Field(default=0.0, description="Base imponible gravada al 27%")
    iva_27: float = Field(default=0.0, description="Importe de IVA liquidado al 27%")
    no_gravado: float = Field(default=0.0, description="Conceptos no gravados")
    exento: float = Field(default=0.0, description="Importes exentos de IVA")
    percepcion_iibb: float = Field(default=0.0, description="Percepciones de Ingresos Brutos")
    percepcion_iibb_jurisdiccion: Optional[str] = Field(default=None, description="Provincia o código de jurisdicción")
    percepcion_iva: float = Field(default=0.0, description="Otras percepciones de IVA")
    impuestos_internos: float = Field(default=0.0, description="Otros tributos o impuestos internos")
    total: float = Field(description="Importe total final de la factura")


class MetaExtraccion(BaseModel):
    confianza_promedio: float = Field(default=1.0, description="Nivel de certidumbre general (0.0 a 1.0)")
    confianza_campos: Dict[str, float] = Field(default_factory=dict, description="Score por campo crítico")


class FacturaExtraidaSchema(BaseModel):
    comprobante: CabeceraComprobanteExtraida
    subtotales: SubtotalesExtraidos
    items: List[ItemFacturaExtraido] = Field(default_factory=list)
    meta: MetaExtraccion = Field(default_factory=MetaExtraccion)


# =====================================================================
# 2. Esquemas de la API REST para el Frontend (RF-19 a RF-29)
# =====================================================================

class AlertaValidacion(BaseModel):
    codigo: str
    campo: str
    mensaje: str
    severidad: str = "warning"  # "warning" o "error"


class ComprobanteItemResponse(BaseModel):
    id: int
    posicion: int
    codigo_insumo: Optional[str] = None
    descripcion: str
    cantidad: float
    unidad_medida: str
    precio_unitario: Decimal
    subtotal_linea: Decimal
    alicuota_iva: Decimal
    cuenta_contable_sugerida: Optional[str] = None
    indicador_iva_sap: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditoriaLogResponse(BaseModel):
    id: int
    usuario: str
    timestamp: datetime
    accion: str
    campo_modificado: Optional[str] = None
    valor_anterior: Optional[str] = None
    valor_nuevo: Optional[str] = None
    detalles: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ComprobanteResponse(BaseModel):
    id: str
    message_id: Optional[str] = None
    archivo_pdf_path: str
    sha256_hash: str
    cuit_emisor: str
    razon_social_emisor: str
    tipo_comprobante: str
    letra: str
    punto_venta: int
    numero_comprobante: int
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    cae: Optional[str] = None
    vencimiento_cae: Optional[date] = None
    cuit_receptor: Optional[str] = None
    moneda: str
    tipo_cambio: Decimal
    neto_gravado_21: Decimal
    neto_gravado_105: Decimal
    neto_gravado_27: Decimal
    no_gravado: Decimal
    exento: Decimal
    iva_21: Decimal
    iva_105: Decimal
    iva_27: Decimal
    percepcion_iibb: Decimal
    percepcion_iibb_jurisdiccion: Optional[str] = None
    percepcion_iva: Decimal
    impuestos_internos: Decimal
    importe_total: Decimal
    orden_compra_nro: Optional[str] = None
    confianza_global: float
    confianza_campos: Dict[str, Any] = Field(default_factory=dict)
    alertas_validacion: List[Any] = Field(default_factory=list)
    estado: EstadoComprobante
    motivo_rechazo: Optional[str] = None
    lote_batch_id: Optional[int] = None
    fecha_creacion: datetime
    items: List[ComprobanteItemResponse] = Field(default_factory=list)
    auditoria_logs: List[AuditoriaLogResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ComprobanteUpdate(BaseModel):
    """Esquema de edición interactiva 1-Click (RF-22)"""
    cuit_emisor: Optional[str] = None
    razon_social_emisor: Optional[str] = None
    punto_venta: Optional[int] = None
    numero_comprobante: Optional[int] = None
    fecha_emision: Optional[date] = None
    cae: Optional[str] = None
    vencimiento_cae: Optional[date] = None
    moneda: Optional[str] = None
    orden_compra_nro: Optional[str] = None
    neto_gravado_21: Optional[Decimal] = None
    neto_gravado_105: Optional[Decimal] = None
    neto_gravado_27: Optional[Decimal] = None
    no_gravado: Optional[Decimal] = None
    exento: Optional[Decimal] = None
    iva_21: Optional[Decimal] = None
    iva_105: Optional[Decimal] = None
    iva_27: Optional[Decimal] = None
    percepcion_iibb: Optional[Decimal] = None
    percepcion_iibb_jurisdiccion: Optional[str] = None
    percepcion_iva: Optional[Decimal] = None
    impuestos_internos: Optional[Decimal] = None
    importe_total: Optional[Decimal] = None
    usuario: str = "analista.contable"


class RechazoComprobante(BaseModel):
    motivo: str
    usuario: str = "analista.contable"


class DashboardMetrics(BaseModel):
    """Métricas del día para el Dashboard Ejecutivo (RF-19)"""
    total_recibidas_hoy: int
    stp_automaticas: int
    porcentaje_stp: float
    pendientes_auditoria: int
    aprobadas_pendientes_lote: int
    rechazadas: int
    monto_lote_ars: Decimal
    monto_lote_usd: Decimal
    total_lotes_historicos: int


class LoteBatchResponse(BaseModel):
    id: int
    nombre_archivo: str
    ruta_archivo: str
    fecha_generacion: datetime
    tipo_disparo: TipoDisparoBatch
    cantidad_facturas: int
    total_ars: Decimal
    total_usd: Decimal
    sha256_hash: str
    resumen_notificacion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrdenCompraItemResponse(BaseModel):
    id: int
    numero_oc: str
    posicion_sap: str
    codigo_insumo: str
    descripcion: str
    cantidad_pedida: float
    cantidad_remanente: float
    unidad_medida: str
    precio_unitario: Decimal
    cuenta_contable_sap: str
    indicador_iva_sap: str

    model_config = ConfigDict(from_attributes=True)


class OrdenCompraResponse(BaseModel):
    numero_oc: str
    cuit_proveedor: str
    estado: str
    moneda: str
    fecha_emision: date
    centro_costo: str
    observaciones: Optional[str] = None
    items: List[OrdenCompraItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProveedorResponse(BaseModel):
    cuit: str
    razon_social: str
    codigo_acreedor_sap: str
    planta_default: str
    contacto_email: Optional[str] = None
    guia_extraccion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
