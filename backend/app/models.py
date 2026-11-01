import enum
import uuid
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Float,
    DateTime,
    Date,
    Text,
    ForeignKey,
    Enum,
    UniqueConstraint,
    JSON,
    func
)
from sqlalchemy.orm import relationship
from app.database import Base


class EstadoComprobante(str, enum.Enum):
    INGESTADO = "INGESTADO"
    EN_PROCESAMIENTO = "EN_PROCESAMIENTO"
    PROCESADA_LISTA_BATCH = "PROCESADA_LISTA_BATCH"
    REQUIERE_AUDITORIA = "REQUIERE_AUDITORIA"
    APROBADA_POR_USUARIO = "APROBADA_POR_USUARIO"
    RECHAZADA = "RECHAZADA"
    CONSOLIDADA_EN_BATCH = "CONSOLIDADA_EN_BATCH"


class TipoDisparoBatch(str, enum.Enum):
    CRON = "CRON"
    MANUAL = "MANUAL"


class Proveedor(Base):
    __tablename__ = "proveedores"

    cuit = Column(String(11), primary_key=True, index=True)  # 11 dígitos sin guiones
    razon_social = Column(String(200), nullable=False)
    codigo_acreedor_sap = Column(String(30), nullable=False, unique=True)  # ej: PROV_30708912345
    planta_default = Column(String(10), default="PL01")  # PL01: Vicente López, PL02: Gral. Rodríguez
    contacto_email = Column(String(120), nullable=True)
    guia_extraccion = Column(Text, nullable=True)  # Few-shot hint

    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    numero_oc = Column(String(20), primary_key=True, index=True)  # ej: 4500098124
    cuit_proveedor = Column(String(11), ForeignKey("proveedores.cuit"), nullable=False)
    estado = Column(String(20), default="ABIERTA")  # ABIERTA / CERRADA
    moneda = Column(String(3), default="ARS")
    fecha_emision = Column(Date, default=date.today)
    centro_costo = Column(String(10), default="PL01")
    observaciones = Column(Text, nullable=True)

    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    items = relationship("OrdenCompraItem", back_populates="orden_compra", cascade="all, delete-orphan")


class OrdenCompraItem(Base):
    __tablename__ = "ordenes_compra_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_oc = Column(String(20), ForeignKey("ordenes_compra.numero_oc"), nullable=False, index=True)
    posicion_sap = Column(String(10), nullable=False)  # 00010, 00020
    codigo_insumo = Column(String(50), nullable=False)  # MP-VET-098
    descripcion = Column(String(250), nullable=False)
    cantidad_pedida = Column(Float, nullable=False)
    cantidad_remanente = Column(Float, nullable=False)
    unidad_medida = Column(String(10), default="KG")
    precio_unitario = Column(Numeric(15, 2), nullable=False)
    cuenta_contable_sap = Column(String(20), default="11040010")  # Cuenta de materia prima
    indicador_iva_sap = Column(String(5), default="V1")  # V1: 21%, V2: 10.5%

    orden_compra = relationship("OrdenCompra", back_populates="items")


class LoteBatch(Base):
    __tablename__ = "lotes_batch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo = Column(String(150), nullable=False)
    ruta_archivo = Column(String(300), nullable=False)
    fecha_generacion = Column(DateTime, default=datetime.utcnow)
    tipo_disparo = Column(Enum(TipoDisparoBatch), default=TipoDisparoBatch.MANUAL)
    cantidad_facturas = Column(Integer, default=0)
    total_ars = Column(Numeric(15, 2), default=0.00)
    total_usd = Column(Numeric(15, 2), default=0.00)
    sha256_hash = Column(String(64), nullable=False)
    resumen_notificacion = Column(Text, nullable=True)

    comprobantes = relationship("Comprobante", back_populates="lote_batch")


class Comprobante(Base):
    __tablename__ = "comprobantes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(255), unique=True, nullable=True, index=True)  # RF-05 anti-duplicados mail
    archivo_pdf_path = Column(String(300), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)  # RF-04

    # Cabecera AFIP (RF-08)
    cuit_emisor = Column(String(11), nullable=False, index=True)
    razon_social_emisor = Column(String(200), nullable=False)
    tipo_comprobante = Column(String(3), nullable=False, default="001")  # 001: Factura A, 006: Factura B
    letra = Column(String(1), default="A")
    punto_venta = Column(Integer, nullable=False)
    numero_comprobante = Column(Integer, nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    cae = Column(String(14), nullable=True)
    vencimiento_cae = Column(Date, nullable=True)
    cuit_receptor = Column(String(11), default="30623368939")
    moneda = Column(String(3), default="ARS")
    tipo_cambio = Column(Numeric(10, 4), default=1.0000)

    # Desglose impositivo contable (RF-09)
    neto_gravado_21 = Column(Numeric(15, 2), default=0.00)
    neto_gravado_105 = Column(Numeric(15, 2), default=0.00)
    neto_gravado_27 = Column(Numeric(15, 2), default=0.00)
    no_gravado = Column(Numeric(15, 2), default=0.00)
    exento = Column(Numeric(15, 2), default=0.00)
    iva_21 = Column(Numeric(15, 2), default=0.00)
    iva_105 = Column(Numeric(15, 2), default=0.00)
    iva_27 = Column(Numeric(15, 2), default=0.00)
    percepcion_iibb = Column(Numeric(15, 2), default=0.00)
    percepcion_iibb_jurisdiccion = Column(String(50), nullable=True)
    percepcion_iva = Column(Numeric(15, 2), default=0.00)
    impuestos_internos = Column(Numeric(15, 2), default=0.00)
    importe_total = Column(Numeric(15, 2), nullable=False)

    # Conciliación OC (RF-11, RF-16)
    orden_compra_nro = Column(String(30), nullable=True, index=True)

    # Calidad y validaciones (RF-12, RF-13, RF-21)
    confianza_global = Column(Float, default=1.0)
    confianza_campos = Column(JSON, default=dict)  # {"cuit_emisor": 0.99, "percepcion_iibb": 0.78}
    alertas_validacion = Column(JSON, default=list)  # [{"codigo": "...", "campo": "...", "mensaje": "..."}]

    # Máquina de estados (RF-18)
    estado = Column(Enum(EstadoComprobante), default=EstadoComprobante.INGESTADO, index=True)
    motivo_rechazo = Column(String(255), nullable=True)

    # Relación con Lote Batch (RF-27)
    lote_batch_id = Column(Integer, ForeignKey("lotes_batch.id"), nullable=True)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Restricción de unicidad estricta fiscal (RF-17)
    __table_args__ = (
        UniqueConstraint(
            "cuit_emisor", "tipo_comprobante", "punto_venta", "numero_comprobante",
            name="uq_comprobante_fiscal"
        ),
    )

    items = relationship("ComprobanteItem", back_populates="comprobante", cascade="all, delete-orphan")
    auditoria_logs = relationship("AuditoriaLog", back_populates="comprobante", cascade="all, delete-orphan")
    lote_batch = relationship("LoteBatch", back_populates="comprobantes")


class ComprobanteItem(Base):
    __tablename__ = "comprobante_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comprobante_id = Column(String(36), ForeignKey("comprobantes.id"), nullable=False, index=True)
    posicion = Column(Integer, default=1)
    codigo_insumo = Column(String(50), nullable=True)
    descripcion = Column(String(250), nullable=False)
    cantidad = Column(Float, nullable=False)
    unidad_medida = Column(String(10), default="KG")
    precio_unitario = Column(Numeric(15, 2), nullable=False)
    subtotal_linea = Column(Numeric(15, 2), nullable=False)
    alicuota_iva = Column(Numeric(5, 2), default=21.00)
    cuenta_contable_sugerida = Column(String(20), default="11040010")
    indicador_iva_sap = Column(String(5), default="V1")

    comprobante = relationship("Comprobante", back_populates="items")


class AuditoriaLog(Base):
    __tablename__ = "auditoria_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comprobante_id = Column(String(36), ForeignKey("comprobantes.id"), nullable=False, index=True)
    usuario = Column(String(80), default="analista.contable")
    timestamp = Column(DateTime, default=datetime.utcnow)
    accion = Column(String(50), nullable=False)  # EDICION, APROBACION_1CLICK, RECHAZO
    campo_modificado = Column(String(60), nullable=True)
    valor_anterior = Column(Text, nullable=True)
    valor_nuevo = Column(Text, nullable=True)
    detalles = Column(Text, nullable=True)

    comprobante = relationship("Comprobante", back_populates="auditoria_logs")
