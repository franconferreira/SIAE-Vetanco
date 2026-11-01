const API_BASE = '/api';

export async function fetchDashboardResumen() {
  const res = await fetch(`${API_BASE}/dashboard/resumen`);
  if (!res.ok) throw new Error('Error al cargar métricas del dashboard');
  return res.json();
}

export async function fetchComprobantes(filtros = {}) {
  const params = new URLSearchParams();
  if (filtros.cuit) params.append('cuit_emisor', filtros.cuit);
  if (filtros.estado) params.append('estado', filtros.estado);
  if (filtros.oc) params.append('orden_compra', filtros.oc);
  if (filtros.search) params.append('search', filtros.search);

  const res = await fetch(`${API_BASE}/comprobantes?${params.toString()}`);
  if (!res.ok) throw new Error('Error al listar comprobantes');
  return res.json();
}

export async function fetchComprobanteDetalle(id) {
  const res = await fetch(`${API_BASE}/comprobantes/${id}`);
  if (!res.ok) throw new Error('Error al cargar detalle del comprobante');
  return res.json();
}

export function getComprobantePdfUrl(id, descargar = false) {
  return `${API_BASE}/comprobantes/${id}/pdf${descargar ? '?descargar=true' : ''}`;
}

export async function aprobarComprobante1Click(id, payload) {
  const res = await fetch(`${API_BASE}/comprobantes/${id}/aprobar`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al aprobar el comprobante');
  }
  return res.json();
}

export async function rechazarComprobante(id, motivo, usuario = 'analista.contable') {
  const res = await fetch(`${API_BASE}/comprobantes/${id}/rechazar`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ motivo, usuario })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al rechazar el comprobante');
  }
  return res.json();
}

export async function subirFacturaPdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('remitente', 'analista.web@vetanco.com');

  const res = await fetch(`${API_BASE}/comprobantes/subir-pdf`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al subir comprobante');
  }
  return res.json();
}

export async function sincronizarCasillaMail() {
  const res = await fetch(`${API_BASE}/ingestor/sincronizar`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Error al sincronizar casilla de correo');
  return res.json();
}

export async function fetchLotesBatch() {
  const res = await fetch(`${API_BASE}/batch`);
  if (!res.ok) throw new Error('Error al listar lotes batch');
  return res.json();
}

export async function generarLoteBatchManual() {
  const res = await fetch(`${API_BASE}/batch/generar`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al generar lote batch');
  }
  return res.json();
}

export async function fetchLotePreview(id) {
  const res = await fetch(`${API_BASE}/batch/${id}/preview`);
  if (!res.ok) throw new Error('Error al previsualizar lote');
  return res.json();
}

export function getLoteDownloadUrl(id) {
  return `${API_BASE}/batch/${id}/descargar`;
}

export async function fetchOrdenesCompra() {
  const res = await fetch(`${API_BASE}/ordenes-compra`);
  if (!res.ok) throw new Error('Error al obtener Órdenes de Compra');
  return res.json();
}

export async function importarMaestroOcCsv(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/ordenes-compra/importar-csv`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al importar maestro de OCs');
  }
  return res.json();
}
