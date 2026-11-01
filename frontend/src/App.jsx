import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ExecutiveDashboard from './components/ExecutiveDashboard';
import InvoiceTable from './components/InvoiceTable';
import SplitViewAuditor from './components/SplitViewAuditor';
import BatchCenterModal from './components/BatchCenterModal';
import ImportOCModal from './components/ImportOCModal';
import UploadInvoiceModal from './components/UploadInvoiceModal';
import LoginScreen from './components/LoginScreen';

import {
  fetchDashboardResumen,
  fetchComprobantes,
  fetchComprobanteDetalle,
  sincronizarCasillaMail
} from './api';

export default function App() {
  // Estado de Autenticación
  const [usuario, setUsuario] = useState(() => {
    try {
      const sesionGuardada = localStorage.getItem('siae_user_session');
      return sesionGuardada ? JSON.parse(sesionGuardada) : null;
    } catch {
      return null;
    }
  });

  const [metrics, setMetrics] = useState(null);
  const [comprobantes, setComprobantes] = useState([]);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingSync, setLoadingSync] = useState(false);

  // Modales
  const [comprobanteSeleccionado, setComprobanteSeleccionado] = useState(null);
  const [mostrarLotes, setMostrarLotes] = useState(false);
  const [mostrarImportarOC, setMostrarImportarOC] = useState(false);
  const [mostrarSubirFactura, setMostrarSubirFactura] = useState(false);

  // Notificación tipo Toast
  const [toast, setToast] = useState(null);

  const mostrarToast = (texto, tipo = 'info') => {
    setToast({ texto, tipo });
    setTimeout(() => setToast(null), 4000);
  };

  const cargarDatos = async () => {
    try {
      const [m, c] = await Promise.all([
        fetchDashboardResumen(),
        fetchComprobantes({ estado: filtroEstado, search: busqueda })
      ]);
      setMetrics(m);
      setComprobantes(c);
    } catch (err) {
      console.error(err);
      mostrarToast('Error conectando con la API de Staging. Verifique que el Backend esté activo.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Heartbeat y Auto-Shutdown al cerrar el navegador (activo siempre)
  useEffect(() => {
    const pingHeartbeat = () => {
      fetch('/api/system/heartbeat', { method: 'POST' }).catch(() => {});
    };
    pingHeartbeat();
    const intervalId = setInterval(pingHeartbeat, 2500);

    const handleBeforeUnload = () => {
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/system/shutdown');
      } else {
        fetch('/api/system/shutdown', { method: 'POST', keepalive: true }).catch(() => {});
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      clearInterval(intervalId);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Cargar datos si el usuario está autenticado
  useEffect(() => {
    if (usuario) {
      cargarDatos();
    }
  }, [usuario, filtroEstado, busqueda]);

  const handleLoginSuccess = (datosSesion) => {
    setUsuario(datosSesion);
    mostrarToast(`Bienvenido al sistema, ${datosSesion.nombre}`, 'success');
  };

  const handleLogout = () => {
    localStorage.removeItem('siae_user_session');
    setUsuario(null);
    mostrarToast('Sesión cerrada correctamente.', 'info');
  };

  const handleSincronizar = async () => {
    setLoadingSync(true);
    try {
      const res = await sincronizarCasillaMail();
      const cant = res.resultado ? res.resultado.procesados : 0;
      mostrarToast(`Sincronización finalizada: ${cant} comprobantes nuevos procesados.`, 'success');
      cargarDatos();
    } catch (err) {
      mostrarToast(`Error de sincronización: ${err.message}`, 'error');
    } finally {
      setLoadingSync(false);
    }
  };

  const handleSeleccionarComprobante = async (id) => {
    try {
      const detalle = await fetchComprobanteDetalle(id);
      setComprobanteSeleccionado(detalle);
    } catch (err) {
      mostrarToast(`Error al abrir comprobante: ${err.message}`, 'error');
    }
  };

  const handleComprobanteActualizado = (actualizado) => {
    mostrarToast(`Comprobante ${actualizado.punto_venta}-${actualizado.numero_comprobante} actualizado a ${actualizado.estado}`, 'success');
    cargarDatos();
  };

  // Si no hay usuario logueado, mostrar pantalla de Login
  if (!usuario) {
    return (
      <>
        {toast && (
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: toast.tipo === 'error' ? '#991b1b' : (toast.tipo === 'success' ? '#166534' : '#1e293b'),
            color: 'white',
            padding: '12px 20px',
            borderRadius: '8px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            fontSize: '13px',
            fontWeight: 600,
            zIndex: 2000
          }}>
            {toast.texto}
          </div>
        )}
        <LoginScreen onLoginSuccess={handleLoginSuccess} />
      </>
    );
  }

  return (
    <div className="app-container">
      {/* Toast Notificación */}
      {toast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          background: toast.tipo === 'error' ? '#991b1b' : (toast.tipo === 'success' ? '#166534' : '#1e293b'),
          color: 'white',
          padding: '12px 20px',
          borderRadius: '8px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
          fontSize: '13px',
          fontWeight: 600,
          zIndex: 2000,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          {toast.texto}
        </div>
      )}

      {/* Header Corporativo con datos de usuario y botón Cerrar Sesión */}
      <Header
        onSincronizar={handleSincronizar}
        onSubirFactura={() => setMostrarSubirFactura(true)}
        onImportarOC={() => setMostrarImportarOC(true)}
        onAbrirLotes={() => setMostrarLotes(true)}
        loadingSync={loadingSync}
        usuario={usuario}
        onLogout={handleLogout}
      />

      {/* Métricas del Día (RF-19) */}
      <ExecutiveDashboard metrics={metrics} />

      {/* Tabla de Facturas y Supervisión (RF-24) */}
      <InvoiceTable
        comprobantes={comprobantes}
        filtroEstado={filtroEstado}
        setFiltroEstado={setFiltroEstado}
        busqueda={busqueda}
        setBusqueda={setBusqueda}
        onSeleccionarComprobante={handleSeleccionarComprobante}
      />

      {/* Split-View Auditor Modal (RF-20, RF-21, RF-22, RF-23) */}
      {comprobanteSeleccionado && (
        <SplitViewAuditor
          comprobante={comprobanteSeleccionado}
          onClose={() => setComprobanteSeleccionado(null)}
          onActualizado={handleComprobanteActualizado}
        />
      )}

      {/* Modal Lotes Batch SAP (RF-26, RF-29) */}
      {mostrarLotes && (
        <BatchCenterModal
          onClose={() => setMostrarLotes(false)}
          onLoteGenerado={cargarDatos}
        />
      )}

      {/* Modal Importar Maestro de OCs SAP */}
      {mostrarImportarOC && (
        <ImportOCModal
          onClose={() => setMostrarImportarOC(false)}
          onImportado={() => {
            mostrarToast('Maestro de OCs cargado correctamente en Staging.', 'success');
            cargarDatos();
          }}
        />
      )}

      {/* Modal Subir Factura PDF */}
      {mostrarSubirFactura && (
        <UploadInvoiceModal
          onClose={() => setMostrarSubirFactura(false)}
          onSubido={() => {
            mostrarToast('Factura PDF ingerida exitosamente.', 'success');
            cargarDatos();
          }}
        />
      )}
    </div>
  );
}
