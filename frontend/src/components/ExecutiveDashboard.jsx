import React from 'react';
import { Inbox, CheckCircle2, AlertTriangle, DollarSign, ArrowUpRight } from 'lucide-react';

export default function ExecutiveDashboard({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="kpi-grid">
      {/* KPI 1: Total Recibidas */}
      <div className="kpi-card blue">
        <div className="kpi-header">
          <span>Facturas Recibidas</span>
          <Inbox size={18} color="#1d4ed8" />
        </div>
        <div className="kpi-value">{metrics.total_recibidas_hoy}</div>
        <div className="kpi-footer">
          <span>Ingestadas hoy vía Gmail IMAP / Bandeja local</span>
        </div>
      </div>

      {/* KPI 2: % STP Automático */}
      <div className="kpi-card green">
        <div className="kpi-header">
          <span>Procesamiento STP</span>
          <CheckCircle2 size={18} color="#16a34a" />
        </div>
        <div className="kpi-value" style={{ color: '#15803d' }}>
          {metrics.porcentaje_stp}%
        </div>
        <div className="kpi-footer">
          <span className="badge badge-stp">
            <ArrowUpRight size={12} /> {metrics.stp_automaticas} facturas 100% automáticas
          </span>
        </div>
      </div>

      {/* KPI 3: Pendientes de Auditoría */}
      <div className="kpi-card amber">
        <div className="kpi-header">
          <span>Pendientes Auditoría</span>
          <AlertTriangle size={18} color="#d97706" />
        </div>
        <div className="kpi-value" style={{ color: metrics.pendientes_auditoria > 0 ? '#b45309' : '#1e1b18' }}>
          {metrics.pendientes_auditoria}
        </div>
        <div className="kpi-footer">
          {metrics.pendientes_auditoria > 0 ? (
            <span className="badge badge-audit">Requieren revisión humana 1-Click</span>
          ) : (
            <span>Bandeja al día sin excepciones</span>
          )}
        </div>
      </div>

      {/* KPI 4: Monto Lote Diario SAP */}
      <div className="kpi-card purple">
        <div className="kpi-header">
          <span>Lote Acumulado SAP</span>
          <DollarSign size={18} color="#7c3aed" />
        </div>
        <div className="kpi-value" style={{ fontSize: '24px' }}>
          ${Number(metrics.monto_lote_ars).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
        </div>
        <div className="kpi-footer">
          <span style={{ fontWeight: 600, color: '#4b5563' }}>
            USD$ {Number(metrics.monto_lote_usd).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </span>
          <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#6b7280' }}>
            {metrics.aprobadas_pendientes_lote} listas p/ exportar
          </span>
        </div>
      </div>
    </div>
  );
}
