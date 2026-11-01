import React, { useState, useEffect } from 'react';
import { X, FileText, Download, Play, CheckCircle, AlertCircle, Code, Shield, Layers } from 'lucide-react';
import { fetchLotesBatch, generarLoteBatchManual, fetchLotePreview, getLoteDownloadUrl, fetchDashboardResumen } from '../api';

export default function BatchCenterModal({ onClose, onLoteGenerado }) {
  const [lotes, setLotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generando, setGenerando] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [mensaje, setMensaje] = useState(null);
  const [pendientesLote, setPendientesLote] = useState(0);

  const cargarDatos = async () => {
    try {
      const [lotesData, resumenData] = await Promise.all([
        fetchLotesBatch(),
        fetchDashboardResumen().catch(() => ({ aprobadas_pendientes_lote: 0 }))
      ]);
      setLotes(lotesData);
      setPendientesLote(resumenData.aprobadas_pendientes_lote || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, []);

  const handleGenerar = async () => {
    setGenerando(true);
    setMensaje(null);
    try {
      const nuevo = await generarLoteBatchManual();
      setMensaje({ tipo: 'ok', texto: `Lote #${nuevo.id} generado exitosamente (${nuevo.cantidad_facturas} comprobantes incluidos)` });
      await cargarDatos();
      if (onLoteGenerado) onLoteGenerado();
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setGenerando(false);
    }
  };

  const handlePreview = async (id) => {
    try {
      const data = await fetchLotePreview(id);
      setPreviewData(data);
    } catch (err) {
      alert('Error cargando previsualización: ' + err.message);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '920px', padding: '26px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--navy-dark)' }}>
              Centro de Lotes Batch — SAP S/4HANA
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Exportación desacoplada masiva (BAPI / LSMW) en texto plano UTF-8 sin BOM (RF-25 a RF-29)
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b' }}>
            <X size={20} />
          </button>
        </div>

        {mensaje && (
          <div
            className={mensaje.tipo === 'ok' ? 'alert-card-warning' : 'alert-card-error'}
            style={{
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              background: mensaje.tipo === 'ok' ? '#f0fdf4' : '#fef2f2',
              color: mensaje.tipo === 'ok' ? '#166534' : '#991b1b',
              border: `1px solid ${mensaje.tipo === 'ok' ? '#bbf7d0' : '#fecaca'}`
            }}
          >
            {mensaje.tipo === 'ok' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
            <span>{mensaje.texto}</span>
          </div>
        )}

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '18px',
          background: 'var(--card-bg)',
          padding: '16px',
          borderRadius: '10px',
          border: '1px solid var(--card-border)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy-dark)' }}>
                Generación de Lote Diario (17:00 hs)
              </span>
              <span style={{
                background: pendientesLote > 0 ? '#dcfce7' : '#f1f5f9',
                color: pendientesLote > 0 ? '#15803d' : '#64748b',
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '11px',
                fontWeight: 700
              }}>
                {pendientesLote} facturas listas para lote
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
              {pendientesLote > 0
                ? "Empaqueta las facturas aprobadas pendientes para su inserción a SAP S/4HANA."
                : "No hay facturas pendientes. Todos los comprobantes aprobados ya fueron consolidados en los lotes anteriores (para evitar duplicación en SAP)."}
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleGenerar}
            disabled={generando || pendientesLote === 0}
            style={{
              opacity: pendientesLote === 0 ? 0.6 : 1,
              cursor: pendientesLote === 0 ? 'not-allowed' : 'pointer'
            }}
            title={pendientesLote === 0 ? "No hay comprobantes pendientes de lote" : "Generar lote ahora"}
          >
            <Play size={16} />
            {generando ? 'Compilando...' : (pendientesLote > 0 ? `Generar Lote (${pendientesLote})` : 'Generar Lote Ahora')}
          </button>
        </div>

        <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: 'var(--navy-dark)' }}>
          Historial de Archivos Lote Generados
        </h3>

        <div className="table-container" style={{ maxHeight: '280px', overflowY: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre de Archivo</th>
                <th>Fecha y Hora</th>
                <th>Disparo</th>
                <th>Facturas</th>
                <th>Monto ARS</th>
                <th>Monto USD</th>
                <th style={{ textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {lotes.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    No hay lotes generados todavía. Pulse "Generar Lote Ahora" para compilar facturas aprobadas.
                  </td>
                </tr>
              ) : (
                lotes.map((lote) => (
                  <tr key={lote.id}>
                    <td style={{ fontWeight: 800 }}>#{lote.id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{lote.nombre_archivo}</td>
                    <td style={{ fontSize: '12px' }}>{new Date(lote.fecha_generacion).toLocaleString()}</td>
                    <td><span className="badge badge-stp">{lote.tipo_disparo}</span></td>
                    <td style={{ fontWeight: 700 }}>{lote.cantidad_facturas}</td>
                    <td style={{ fontWeight: 600 }}>${Number(lote.total_ars).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
                    <td style={{ fontWeight: 600 }}>USD$ {Number(lote.total_usd).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <button
                        className="btn btn-light"
                        style={{ padding: '4px 8px', fontSize: '11px', marginRight: '6px' }}
                        onClick={() => handlePreview(lote.id)}
                        title="Ver líneas 01;KR y 02;31/40"
                      >
                        <Code size={13} /> Previa
                      </button>
                      <a
                        href={getLoteDownloadUrl(lote.id)}
                        className="btn btn-success"
                        style={{ padding: '4px 8px', fontSize: '11px', textDecoration: 'none' }}
                        title="Descargar archivo CSV plano para SAP"
                      >
                        <Download size={13} /> BAPI
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Modal de Previsualización de Registros SAP BKPF y BSEG */}
        {previewData && (
          <div style={{ marginTop: '20px', background: '#0f172a', color: '#f8fafc', padding: '16px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                Estructura de Registros: {previewData.nombre_archivo} (SHA-256: {previewData.sha256.slice(0, 16)}...)
              </span>
              <button
                onClick={() => setPreviewData(null)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
              >
                <X size={16} />
              </button>
            </div>
            <pre style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              maxHeight: '180px',
              overflowY: 'auto',
              background: '#1e293b',
              padding: '12px',
              borderRadius: '6px',
              lineHeight: 1.6
            }}>
              {previewData.contenido}
            </pre>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button className="btn btn-light" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
