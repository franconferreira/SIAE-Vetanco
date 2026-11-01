import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  ZoomIn,
  ZoomOut,
  RotateCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  History,
  ShieldCheck,
  Calculator,
  Save,
  Download
} from 'lucide-react';
import { getComprobantePdfUrl, aprobarComprobante1Click, rechazarComprobante } from '../api';

export default function SplitViewAuditor({ comprobante, onClose, onActualizado }) {
  if (!comprobante) return null;

  // Estados del visor PDF
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);

  // Estados del formulario editable
  const [formData, setFormData] = useState({
    punto_venta: comprobante.punto_venta || 1,
    numero_comprobante: comprobante.numero_comprobante || 1,
    cae: comprobante.cae || '',
    vencimiento_cae: comprobante.vencimiento_cae || '',
    orden_compra_nro: comprobante.orden_compra_nro || '',
    neto_gravado_21: Number(comprobante.neto_gravado_21 || 0),
    neto_gravado_105: Number(comprobante.neto_gravado_105 || 0),
    neto_gravado_27: Number(comprobante.neto_gravado_27 || 0),
    no_gravado: Number(comprobante.no_gravado || 0),
    exento: Number(comprobante.exento || 0),
    iva_21: Number(comprobante.iva_21 || 0),
    iva_105: Number(comprobante.iva_105 || 0),
    iva_27: Number(comprobante.iva_27 || 0),
    percepcion_iibb: Number(comprobante.percepcion_iibb || 0),
    percepcion_iibb_jurisdiccion: comprobante.percepcion_iibb_jurisdiccion || 'Buenos Aires',
    percepcion_iva: Number(comprobante.percepcion_iva || 0),
    impuestos_internos: Number(comprobante.impuestos_internos || 0),
    importe_total: Number(comprobante.importe_total || 0),
    usuario: 'analista.franco'
  });

  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [mostrarModalRechazo, setMostrarModalRechazo] = useState(false);
  const [motivoRechazo, setMotivoRechazo] = useState('Error de proveedor en alícuota o suma');

  // Recálculo matemático contable reactivo en vivo (RF-13, RF-22)
  const sumaCalculada = useMemo(() => {
    const total =
      Number(formData.neto_gravado_21 || 0) +
      Number(formData.neto_gravado_105 || 0) +
      Number(formData.neto_gravado_27 || 0) +
      Number(formData.no_gravado || 0) +
      Number(formData.exento || 0) +
      Number(formData.iva_21 || 0) +
      Number(formData.iva_105 || 0) +
      Number(formData.iva_27 || 0) +
      Number(formData.percepcion_iibb || 0) +
      Number(formData.percepcion_iva || 0) +
      Number(formData.impuestos_internos || 0);
    return Math.round(total * 100) / 100;
  }, [formData]);

  const diferenciaImpositiva = useMemo(() => {
    return Math.round(Math.abs(sumaCalculada - Number(formData.importe_total || 0)) * 100) / 100;
  }, [sumaCalculada, formData.importe_total]);

  const cuadreExacto = diferenciaImpositiva <= 0.02;

  // Determinar campos observados por baja confianza o regla fallida (RF-21)
  const camposObservados = useMemo(() => {
    const obs = new Set();
    if (comprobante.confianza_campos) {
      for (const [k, v] of Object.entries(comprobante.confianza_campos)) {
        if (v < 0.95) obs.add(k);
      }
    }
    if (comprobante.alertas_validacion) {
      for (const a of comprobante.alertas_validacion) {
        if (a.campo) obs.add(a.campo);
      }
    }
    if (!cuadreExacto) {
      obs.add('importe_total');
    }
    return obs;
  }, [comprobante, cuadreExacto]);

  const handleInputChange = (campo, valor) => {
    setFormData((prev) => ({
      ...prev,
      [campo]: valor
    }));
  };

  const handleAprobar1Click = async () => {
    setSaving(true);
    setErrorMsg(null);
    try {
      const resp = await aprobarComprobante1Click(comprobante.id, formData);
      onActualizado(resp);
      onClose();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRechazar = async () => {
    setSaving(true);
    setErrorMsg(null);
    try {
      const resp = await rechazarComprobante(comprobante.id, motivoRechazo, formData.usuario);
      onActualizado(resp);
      onClose();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setSaving(false);
    }
  };

  const pdfUrl = getComprobantePdfUrl(comprobante.id);

  return (
    <div className="modal-overlay">
      <div className="modal-content split-view-modal">
        {/* Cabecera del Split-View */}
        <div style={{
          padding: '16px 24px',
          background: 'linear-gradient(135deg, var(--navy-dark) 0%, var(--navy-mid) 100%)',
          color: 'white',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #334155'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="brand-badge">Auditoría 1-Click Split-View</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#93c5fd' }}>
                Factura {comprobante.letra} {String(comprobante.punto_venta).padStart(4, '0')}-{String(comprobante.numero_comprobante).padStart(8, '0')}
              </span>
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>| {comprobante.razon_social_emisor}</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Estado Actual: <strong style={{ color: 'white' }}>{comprobante.estado}</strong>
            </span>
            <button
              onClick={onClose}
              style={{ background: 'transparent', color: '#94a3b8', padding: '4px' }}
              title="Cerrar visor"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Cuerpo Dividido (50% PDF, 50% Formulario) */}
        <div className="split-view-body">
          {/* PANEL IZQUIERDO: Visor PDF interactivo */}
          <div className="split-pane-left">
            <div style={{
              background: '#1e293b',
              padding: '8px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: 'white',
              fontSize: '12px',
              borderBottom: '1px solid #334155'
            }}>
              <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={14} color="#38bdf8" /> Comprobante Original Digital AFIP
              </span>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                  onClick={() => setZoom((z) => Math.max(50, z - 15))}
                  title="Alejar"
                >
                  <ZoomOut size={13} />
                </button>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{zoom}%</span>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                  onClick={() => setZoom((z) => Math.min(200, z + 15))}
                  title="Acercar"
                >
                  <ZoomIn size={13} />
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                  onClick={() => setRotation((r) => (r + 90) % 360)}
                  title="Rotar 90°"
                >
                  <RotateCw size={13} />
                </button>
                <a
                  href={getComprobantePdfUrl(comprobante.id, true)}
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px', textDecoration: 'none' }}
                  title="Descargar archivo PDF"
                >
                  <Download size={13} />
                </a>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '4px 8px', fontSize: '11px', textDecoration: 'none' }}
                  title="Abrir en pestaña nueva"
                >
                  <ExternalLink size={13} />
                </a>
              </div>
            </div>

            <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#475569' }}>
              <iframe
                src={`${pdfUrl}#zoom=${zoom}&view=FitH`}
                title="Visor PDF Comprobante"
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  transform: `rotate(${rotation}deg)`,
                  transition: 'transform 0.2s'
                }}
              />
            </div>
          </div>

          {/* PANEL DERECHO: Formulario de Auditoría y Validación en Caliente */}
          <div className="split-pane-right">
            {/* Alertas de Incertidumbre y Errores (RF-21) */}
            {comprobante.alertas_validacion && comprobante.alertas_validacion.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {comprobante.alertas_validacion.map((alerta, idx) => (
                  <div
                    key={idx}
                    className={alerta.severidad === 'error' ? 'alert-card-error' : 'alert-card-warning'}
                  >
                    <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <strong style={{ display: 'block', textTransform: 'uppercase', fontSize: '11px' }}>
                        {alerta.codigo.replace(/_/g, ' ')}
                      </strong>
                      <span>{alerta.mensaje}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {errorMsg && (
              <div className="alert-card-error">
                <XCircle size={18} style={{ flexShrink: 0 }} />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* SECCIÓN 1: Datos de Cabecera AFIP */}
            <div style={{ background: 'white', padding: '16px', borderRadius: '10px', border: '1px solid var(--card-border)' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 800, marginBottom: '12px', color: 'var(--navy-mid)' }}>
                1. Datos de Cabecera Fiscal (AFIP / ARCA)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', fontSize: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Pto. Venta</label>
                  <input
                    type="number"
                    value={formData.punto_venta}
                    onChange={(e) => handleInputChange('punto_venta', Number(e.target.value))}
                    className={camposObservados.has('punto_venta') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Nro. Factura</label>
                  <input
                    type="number"
                    value={formData.numero_comprobante}
                    onChange={(e) => handleInputChange('numero_comprobante', Number(e.target.value))}
                    className={camposObservados.has('numero_comprobante') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Orden de Compra</label>
                  <input
                    type="text"
                    value={formData.orden_compra_nro}
                    onChange={(e) => handleInputChange('orden_compra_nro', e.target.value)}
                    className={camposObservados.has('orden_compra_nro') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontWeight: 600 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>CAE (14 dígitos)</label>
                  <input
                    type="text"
                    value={formData.cae}
                    onChange={(e) => handleInputChange('cae', e.target.value)}
                    className={camposObservados.has('cae') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontFamily: 'var(--font-mono)' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Vto. CAE</label>
                  <input
                    type="text"
                    value={formData.vencimiento_cae || ''}
                    onChange={(e) => handleInputChange('vencimiento_cae', e.target.value)}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Moneda</label>
                  <input
                    type="text"
                    value={comprobante.moneda}
                    disabled
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#f8fafc' }}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN 2: Ítems de Materia Prima Extraídos */}
            {comprobante.items && comprobante.items.length > 0 && (
              <div style={{ background: 'white', padding: '16px', borderRadius: '10px', border: '1px solid var(--card-border)' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 800, marginBottom: '10px', color: 'var(--navy-mid)' }}>
                  2. Detalle de Materia Prima Facturada
                </h3>
                <div style={{ maxHeight: '140px', overflowY: 'auto' }}>
                  <table style={{ fontSize: '12px' }}>
                    <thead>
                      <tr>
                        <th>Código</th>
                        <th>Descripción</th>
                        <th>Cant.</th>
                        <th>Precio Unit.</th>
                        <th>Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comprobante.items.map((it) => (
                        <tr key={it.id}>
                          <td style={{ fontFamily: 'var(--font-mono)' }}>{it.codigo_insumo || '-'}</td>
                          <td>{it.descripcion}</td>
                          <td>{it.cantidad} {it.unidad_medida}</td>
                          <td>${Number(it.precio_unitario).toFixed(2)}</td>
                          <td style={{ fontWeight: 600 }}>${Number(it.subtotal_linea).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SECCIÓN 3: Desglose Impositivo con Recálculo en Vivo (RF-22) */}
            <div style={{ background: 'white', padding: '18px', borderRadius: '10px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 800, color: 'var(--navy-mid)' }}>
                  3. Desglose Impositivo y Cuadre Matemático
                </h3>
                <span style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Calculator size={13} /> Tolerancia estricta ± $0.02
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', fontSize: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>Neto Gravado 21%</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.neto_gravado_21}
                    onChange={(e) => handleInputChange('neto_gravado_21', Number(e.target.value))}
                    className={camposObservados.has('neto_gravado_21') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>IVA Liquidado 21%</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.iva_21}
                    onChange={(e) => handleInputChange('iva_21', Number(e.target.value))}
                    className={camposObservados.has('iva_21') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontWeight: 700, marginBottom: '4px' }}>
                    Percepción IIBB {formData.percepcion_iibb_jurisdiccion ? `(${formData.percepcion_iibb_jurisdiccion})` : ''}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.percepcion_iibb}
                    onChange={(e) => handleInputChange('percepcion_iibb', Number(e.target.value))}
                    className={camposObservados.has('percepcion_iibb') ? 'input-warning' : ''}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                  />
                </div>
              </div>

              {/* Caja de Balance y Cuadre Matemático Reactivo en Vivo */}
              <div style={{
                marginTop: '16px',
                padding: '12px 16px',
                borderRadius: '8px',
                background: cuadreExacto ? 'var(--green-bg)' : 'var(--red-bg)',
                border: `1.5px solid ${cuadreExacto ? 'var(--green-border)' : 'var(--red-border)'}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px'
              }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: cuadreExacto ? 'var(--green-text)' : 'var(--red-text)' }}>
                    {cuadreExacto ? '✔ Cuadre Matemático Válido' : '✖ Discrepancia en Suma Impositiva'}
                  </span>
                  <div style={{ fontSize: '12px', color: '#334155' }}>
                    Suma Calculada: <strong>${sumaCalculada.toFixed(2)}</strong> | Total Factura: <strong>${Number(formData.importe_total).toFixed(2)}</strong>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)' }}>
                    Total Facturado
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.importe_total}
                    onChange={(e) => handleInputChange('importe_total', Number(e.target.value))}
                    className={!cuadreExacto ? 'input-error' : ''}
                    style={{
                      fontSize: '16px',
                      fontWeight: 800,
                      width: '140px',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      textAlign: 'right',
                      border: '1.5px solid #cbd5e1'
                    }}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN 4: Botones de Acción (1-Click Approval / Rechazar) */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', alignItems: 'center' }}>
              <button
                className="btn btn-danger"
                onClick={() => setMostrarModalRechazo(true)}
                disabled={saving}
              >
                <XCircle size={16} />
                Rechazar Comprobante
              </button>

              <button
                className="btn btn-success"
                onClick={handleAprobar1Click}
                disabled={saving || !cuadreExacto}
                style={{ padding: '10px 24px', fontSize: '14px' }}
                title={cuadreExacto ? 'Aprueba e incluye en lote SAP' : 'Debe corregir la discrepancia de suma antes de aprobar'}
              >
                <CheckCircle2 size={18} />
                {saving ? 'Guardando...' : 'Aprobar y Mover a Batch (1-Click)'}
              </button>
            </div>

            {/* SECCIÓN 5: Pista de Auditoría (Audit Trail RF-23) */}
            {comprobante.auditoria_logs && comprobante.auditoria_logs.length > 0 && (
              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <History size={14} /> Pista de Auditoría y Trazabilidad (Audit Trail)
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                  {comprobante.auditoria_logs.map((log) => (
                    <div key={log.id} style={{ color: '#475569', borderBottom: '1px dashed #cbd5e1', paddingBottom: '4px' }}>
                      <strong>{new Date(log.timestamp).toLocaleString()}</strong> [{log.usuario}] — {log.accion}: {log.campo_modificado || ''} {log.valor_anterior && `(Antes: ${log.valor_anterior} -> Ahora: ${log.valor_nuevo})`}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Rechazo Comprobante */}
        {mostrarModalRechazo && (
          <div className="modal-overlay" style={{ zIndex: 1100 }}>
            <div className="modal-content" style={{ maxWidth: '450px', padding: '24px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--red-text)', marginBottom: '12px' }}>
                Rechazar Comprobante Fiscal
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Seleccione el motivo de rechazo que quedará registrado en la pista de auditoría:
              </p>
              <select
                value={motivoRechazo}
                onChange={(e) => setMotivoRechazo(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', marginBottom: '20px' }}
              >
                <option value="Factura ilegible o corrupta">Factura ilegible o corrupta</option>
                <option value="Error de proveedor en alícuota o suma">Error de proveedor en alícuota o suma</option>
                <option value="Sin Orden de Compra válida en SAP">Sin Orden de Compra válida en SAP</option>
                <option value="Precio unitario excede lo pactado en OC">Precio unitario excede lo pactado en OC</option>
                <option value="Comprobante no dirigido a Vetanco S.A.">Comprobante no dirigido a Vetanco S.A.</option>
              </select>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button className="btn btn-light" onClick={() => setMostrarModalRechazo(false)}>
                  Cancelar
                </button>
                <button className="btn btn-danger" onClick={handleRechazar} disabled={saving}>
                  Confirmar Rechazo
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
