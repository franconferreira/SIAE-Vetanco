import React, { useState, useRef } from 'react';
import { X, Upload, FileText, CheckCircle, AlertCircle, FileCheck, RefreshCw } from 'lucide-react';
import { subirFacturaPdf } from '../api';

export default function UploadInvoiceModal({ onClose, onSubido }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.toLowerCase().endsWith('.pdf') || droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setMensaje(null);
      } else {
        setMensaje({ tipo: 'error', texto: 'El archivo seleccionado no es un PDF válido. Por favor cargue comprobantes en formato PDF.' });
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setMensaje(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setMensaje(null);
    try {
      const resp = await subirFacturaPdf(file);
      setMensaje({
        tipo: 'ok',
        texto: `Comprobante ingresado exitosamente con ID ${resp.id.slice(0, 8)}... (${resp.estado})`
      });
      if (onSubido) onSubido();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message });
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="modal-overlay" onDragOver={(e) => e.preventDefault()} onDrop={(e) => e.preventDefault()}>
      <div className="modal-content" style={{ maxWidth: '540px', padding: '26px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy-dark)' }}>
              Subir Factura de Proveedor (PDF)
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Procesamiento directo e ingesta en segundo plano (Simulación o contingencia)
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
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              lineHeight: '1.45',
              background: mensaje.tipo === 'ok' ? '#f0fdf4' : '#fef2f2',
              color: mensaje.tipo === 'ok' ? '#166534' : '#991b1b',
              border: `1px solid ${mensaje.tipo === 'ok' ? '#bbf7d0' : '#fecaca'}`
            }}
          >
            {mensaje.tipo === 'ok' ? <CheckCircle size={20} style={{ flexShrink: 0, marginTop: '1px' }} /> : <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '1px' }} />}
            <span>{mensaje.texto}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: isDragging ? '2px dashed #2563eb' : '2px dashed var(--card-border-strong)',
              borderRadius: '10px',
              padding: '28px 20px',
              textAlign: 'center',
              background: isDragging ? '#eff6ff' : '#f8fafc',
              cursor: 'pointer',
              marginBottom: '16px',
              transition: 'all 0.2s ease-in-out'
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            {!file ? (
              <>
                <FileText
                  size={42}
                  color={isDragging ? '#2563eb' : '#64748b'}
                  style={{ margin: '0 auto 10px', transition: 'color 0.2s ease' }}
                />
                <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                  {isDragging ? '¡Soltá el archivo PDF aquí!' : 'Hacé clic o arrastrá el archivo PDF aquí'}
                </p>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0' }}>
                  Normativa ARCA / AFIP (Facturas A, B o C digitales de proveedores)
                </p>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '14px' }}>
                <FileCheck size={36} color="#16a34a" />
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-dark)' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {formatFileSize(file.size)} • PDF listo para procesar
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  style={{
                    background: '#f1f5f9',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    cursor: 'pointer',
                    color: '#475569',
                    marginLeft: '8px'
                  }}
                >
                  Cambiar
                </button>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-light" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={!file || loading}>
              {loading ? (
                <>
                  <RefreshCw size={16} className="spin-animate" />
                  Analizando y validando...
                </>
              ) : (
                <>
                  <Upload size={16} />
                  Ingestar y Procesar
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
