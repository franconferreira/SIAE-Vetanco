import React from 'react';
import { Upload, FileText, Database, ShieldCheck, Mail, LogOut, User } from 'lucide-react';

export default function Header({
  onSincronizar,
  onSubirFactura,
  onImportarOC,
  onAbrirLotes,
  loadingSync,
  usuario,
  onLogout
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

      <div className="header-actions" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        {/* Perfil del Usuario Activo & Cerrar Sesión */}
        {usuario && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(255, 255, 255, 0.08)',
            padding: '5px 12px 5px 6px',
            borderRadius: '24px',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            marginRight: '6px'
          }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '11px',
              color: '#ffffff'
            }}>
              FF
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>
                {usuario.nombre || 'Franco Ferreira'}
              </span>
              <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>
                {usuario.rol || 'Analista AP'}
              </span>
            </div>
            <button
              onClick={onLogout}
              style={{
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#fca5a5',
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                cursor: 'pointer',
                marginLeft: '4px',
                transition: 'all 0.2s'
              }}
              title="Cerrar sesión y volver al login"
            >
              <LogOut size={12} /> Salir
            </button>
          </div>
        )}

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
