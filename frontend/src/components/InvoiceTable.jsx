import React from 'react';
import { Search, Eye, AlertCircle, FileCheck, Check, Clock, XCircle, FileSpreadsheet, X } from 'lucide-react';

export default function InvoiceTable({
  comprobantes,
  filtroEstado,
  setFiltroEstado,
  busqueda,
  setBusqueda,
  onSeleccionarComprobante,
  onEliminarComprobante
}) {
  const getBadgeClass = (estado) => {
    switch (estado) {
      case 'PROCESADA_LISTA_BATCH': return 'badge-stp';
      case 'REQUIERE_AUDITORIA': return 'badge-audit';
      case 'APROBADA_POR_USUARIO': return 'badge-approved';
      case 'CONSOLIDADA_EN_BATCH': return 'badge-batch';
      case 'RECHAZADA': return 'badge-rejected';
      default: return 'badge-light';
    }
  };

  const getEstadoTexto = (estado) => {
    switch (estado) {
      case 'PROCESADA_LISTA_BATCH': return 'Lista Lote (STP)';
      case 'REQUIERE_AUDITORIA': return 'Requiere Auditoría';
      case 'APROBADA_POR_USUARIO': return 'Aprobada p/ Usuario';
      case 'CONSOLIDADA_EN_BATCH': return 'Exportada a SAP';
      case 'RECHAZADA': return 'Rechazada';
      default: return estado;
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)' }}>
            Bandeja de Comprobantes de Materia Prima
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Supervisión, auditoría y conciliación de comprobantes en base de datos Staging
          </p>
        </div>

        {/* Barra de filtros */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '10px' }} />
            <input
              type="text"
              placeholder="Buscar por Proveedor, CUIT, OC o CAE..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 36px',
                borderRadius: '8px',
                border: '1px solid var(--card-border-strong)',
                fontSize: '13px',
                background: 'white'
              }}
            />
          </div>

          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--card-border-strong)',
              fontSize: '13px',
              background: 'white',
              fontWeight: 600,
              color: 'var(--text-main)'
            }}
          >
            <option value="">Todos los Estados</option>
            <option value="REQUIERE_AUDITORIA">Requiere Auditoría</option>
            <option value="PROCESADA_LISTA_BATCH">Lista Lote (STP 100%)</option>
            <option value="APROBADA_POR_USUARIO">Aprobada por Usuario</option>
            <option value="CONSOLIDADA_EN_BATCH">Consolidada en SAP</option>
            <option value="RECHAZADA">Rechazada</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Proveedor / Emisor</th>
              <th>Comprobante</th>
              <th>Emisión</th>
              <th>Orden de Compra</th>
              <th>Total Facturado</th>
              <th>Confianza IA</th>
              <th>Alertas / Reglas</th>
              <th>Estado</th>
              <th style={{ textAlign: 'right' }}>Acción</th>
            </tr>
          </thead>
          <tbody>
            {comprobantes.length === 0 ? (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                  No se encontraron comprobantes con los filtros seleccionados.
                </td>
              </tr>
            ) : (
              comprobantes.map((c) => {
                const tieneAlertas = c.alertas_validacion && c.alertas_validacion.length > 0;
                const confPorc = Math.round(c.confianza_global * 100);

                return (
                  <tr key={c.id}>
                    <td>
                      <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                        {c.razon_social_emisor}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        CUIT: {c.cuit_emisor}
                      </div>
                    </td>

                    <td>
                      <span style={{ fontWeight: 600 }}>Factura {c.letra}</span>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                        {String(c.punto_venta).padStart(4, '0')}-{String(c.numero_comprobante).padStart(8, '0')}
                      </div>
                    </td>

                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>
                      {c.fecha_emision}
                    </td>

                    <td>
                      {c.orden_compra_nro ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#1d4ed8' }}>
                          {c.orden_compra_nro}
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#64748b', fontStyle: 'italic' }}>
                          Sin OC (Servicios/Directo)
                        </span>
                      )}
                    </td>

                    <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                      {c.moneda === 'USD' ? 'USD$ ' : '$ '}
                      {Number(c.importe_total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
                    </td>

                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{
                          width: '50px',
                          height: '6px',
                          background: '#e2e8f0',
                          borderRadius: '3px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${confPorc}%`,
                            height: '100%',
                            background: confPorc >= 95 ? '#16a34a' : (confPorc >= 80 ? '#d97706' : '#dc2626')
                          }} />
                        </div>
                        <span style={{ fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                          {confPorc}%
                        </span>
                      </div>
                    </td>

                    <td>
                      {tieneAlertas ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <AlertCircle size={15} color="#d97706" />
                          <span style={{ fontSize: '11px', color: '#b45309', fontWeight: 600 }}>
                            {c.alertas_validacion[0].codigo.replace(/_/g, ' ')}
                            {c.alertas_validacion.length > 1 && ` (+${c.alertas_validacion.length - 1})`}
                          </span>
                        </div>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Check size={14} /> Validación limpia
                        </span>
                      )}
                    </td>

                    <td>
                      <span className={`badge ${getBadgeClass(c.estado)}`}>
                        {getEstadoTexto(c.estado)}
                      </span>
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          className="btn btn-primary"
                          onClick={() => onSeleccionarComprobante(c.id)}
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                        >
                          <Eye size={14} />
                          Auditar Split-View
                        </button>
                        {onEliminarComprobante && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const desc = `${c.letra} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')} (${c.razon_social_emisor})`;
                              if (window.confirm(`¿Deseas eliminar la factura ${desc} de la lista para volver a probarla?`)) {
                                onEliminarComprobante(c.id, desc);
                              }
                            }}
                            style={{
                              background: '#fee2e2',
                              border: '1px solid #fecaca',
                              color: '#dc2626',
                              borderRadius: '6px',
                              padding: '6px 8px',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              transition: 'all 0.15s ease'
                            }}
                            title="Eliminar factura de la lista para volver a probarla"
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = '#fecaca';
                              e.currentTarget.style.color = '#b91c1c';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = '#fee2e2';
                              e.currentTarget.style.color = '#dc2626';
                            }}
                          >
                            <X size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
