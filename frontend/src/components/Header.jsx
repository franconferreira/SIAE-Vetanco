import React from 'react';
import { RefreshCw, Upload, FileText, Database, ShieldCheck, Mail } from 'lucide-react';

export default function Header({
  onSincronizar,
  onSubirFactura,
  onImportarOC,
  onAbrirLotes,
  loadingSync
}) {
  return (
    <header className="header-card">
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <span className="brand-badge">Vetanco S.A.</span>
          <span style={{ fontSize: '12px', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={14} color="#38bdf8" /> CUIT: 30-62336893-9 | SAP S/4HANA Staging
          </span>
        </div>
        <div className="header-title">
          <h1>SIAE-Vetanco</h1>
        </div>
        <p className="header-subtitle">
          Sistema Inteligente de Automatización y Extracción de Facturas de Materia Prima para SAP S/4HANA (Grupo 8 - UADE)
        </p>
      </div>

      <div className="header-actions">
        <button
          className="btn btn-secondary"
          onClick={onSincronizar}
          disabled={loadingSync}
          title="Escanea casilla Gmail IMAP puerto 993 y bandeja local"
        >
          <Mail size={16} />
          {loadingSync ? 'Sincronizando...' : 'Escanear Casilla'}
        </button>

        <button className="btn btn-light" onClick={onSubirFactura} title="Carga manual de factura PDF">
          <Upload size={16} />
          Subir Factura PDF
        </button>

        <button className="btn btn-light" onClick={onImportarOC} title="Carga maestro semanal exportado de SAP">
          <Database size={16} />
          Importar OCs SAP
        </button>

        <button className="btn btn-primary" onClick={onAbrirLotes} title="Ver y generar lotes Batch para SAP">
          <FileText size={16} />
          Lotes Batch SAP
        </button>
      </div>
    </header>
  );
}
