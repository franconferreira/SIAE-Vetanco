import React, { useState, useRef } from 'react';
import { X, Upload, Database, CheckCircle, AlertCircle, FileSpreadsheet, RefreshCw, FileCheck } from 'lucide-react';
import { importarMaestroOcCsv } from '../api';

export default function ImportOCModal({ onClose, onImportado }) {
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
      if (droppedFile.name.toLowerCase().endsWith('.csv') || droppedFile.type.includes('csv') || droppedFile.type.includes('excel')) {
        setFile(droppedFile);
        setMensaje(null);
      } else {
        setMensaje({ tipo: 'error', texto: 'El archivo seleccionado no es un CSV válido. Debe ser el archivo exportado de SAP (.csv).' });
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
      const resp = await importarMaestroOcCsv(file);
      setMensaje({
        tipo: 'ok',
        texto: `Maestro importado con éxito: ${resp.filas_procesadas} posiciones cargadas en Staging.`
      });
      if (onImportado) onImportado();
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
              Importar Reporte Maestro de OCs SAP
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Carga semanal del archivo CSV de SAP S/4HANA (3-Way Matching Staging)
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
              border: isDragging ? '2px dashed #0284c7' : '2px dashed var(--card-border-strong)',
              borderRadius: '10px',
              padding: '28px 20px',
              textAlign: 'center',
              background: isDragging ? '#f0f9ff' : '#f8fafc',
              cursor: 'pointer',
              marginBottom: '16px',
              transition: 'all 0.2s ease-in-out'
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            {!file ? (
              <>
                <FileSpreadsheet
                  size={42}
                  color={isDragging ? '#0284c7' : '#64748b'}
                  style={{ margin: '0 auto 10px', transition: 'color 0.2s ease' }}
                />
                <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                  {isDragging ? '¡Soltá el archivo CSV aquí!' : 'Hacé clic o arrastrá el archivo CSV aquí'}
                </p>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0' }}>
                  Delimitado por punto y coma (;) con columnas EBELN, LIFNR, MATNR, cantidad y precios
                </p>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '14px' }}>
                <FileCheck size={36} color="#0284c7" />
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-dark)' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {formatFileSize(file.size)} • Archivo CSV listo para importar
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
                  Cargando en BD...
                </>
              ) : (
                <>
                  <Upload size={16} />
                  Importar a Staging
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
