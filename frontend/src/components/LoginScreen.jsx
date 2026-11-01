import React, { useState, useEffect } from 'react';
import { Mail, Lock, LogIn, Eye, EyeOff, ShieldCheck, AlertCircle, Key, CheckCircle2 } from 'lucide-react';

const CASILLA_OFICIAL = "facturas.proveedores.franco@gmail.com";
const CASILLA_TEST = "facturas.proveedores.test.franco@gmail.com";
const PASSWORD_CORRECTA = "12345";

export default function LoginScreen({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [recordar, setRecordar] = useState(true);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  // Al montar, cargar credenciales previamente guardadas si ya se logueó antes
  useEffect(() => {
    const savedEmail = localStorage.getItem('siae_saved_email');
    const savedPassword = localStorage.getItem('siae_saved_password');

    if (savedEmail) {
      setEmail(savedEmail);
      if (savedPassword) {
        setPassword(savedPassword);
      }
    } else {
      // Valor por defecto sugerido para la primera vez
      setEmail(CASILLA_OFICIAL);
      setPassword(PASSWORD_CORRECTA);
    }
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    setCargando(true);

    setTimeout(() => {
      const emailTrim = email.trim().toLowerCase();
      
      // Validar correo
      const esEmailValido = emailTrim === CASILLA_OFICIAL.toLowerCase() || 
                            emailTrim === CASILLA_TEST.toLowerCase() ||
                            emailTrim.includes('@vetanco.com') ||
                            emailTrim.includes('franco');

      if (!esEmailValido) {
        setError(`Correo no autorizado. Debe utilizar la casilla de proveedores (${CASILLA_OFICIAL}) o una cuenta corporativa.`);
        setCargando(false);
        return;
      }

      // Validar contraseña
      if (password !== PASSWORD_CORRECTA) {
        setError('Contraseña incorrecta. (Pista demo: 12345)');
        setCargando(false);
        return;
      }

      // Guardar en localStorage si está tildado recordar
      if (recordar) {
        localStorage.setItem('siae_saved_email', emailTrim);
        localStorage.setItem('siae_saved_password', password);
        localStorage.setItem('siae_recordar_credenciales', 'true');
      } else {
        localStorage.removeItem('siae_saved_password');
        localStorage.setItem('siae_saved_email', emailTrim);
      }

      // Guardar sesión activa
      const sesionData = {
        email: emailTrim,
        nombre: 'Franco Ferreira',
        rol: 'Analista de Cuentas a Pagar (AP)',
        cuit: '30-62336893-9',
        loginTime: new Date().toISOString()
      };
      localStorage.setItem('siae_user_session', JSON.stringify(sesionData));

      setCargando(false);
      onLoginSuccess(sesionData);
    }, 400);
  };

  const autocompletarDemo = () => {
    setEmail(CASILLA_OFICIAL);
    setPassword(PASSWORD_CORRECTA);
    setError('');
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0b151f 0%, #152433 50%, #1c3247 100%)',
      padding: '24px',
      fontFamily: 'var(--font, -apple-system, BlinkMacSystemFont, sans-serif)'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '460px',
        background: '#ffffff',
        borderRadius: '16px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)',
        overflow: 'hidden'
      }}>
        {/* Cabecera del formulario con estética Vetanco */}
        <div style={{
          background: 'linear-gradient(135deg, #12202c 0%, #1f3347 100%)',
          color: '#ffffff',
          padding: '32px 32px 28px',
          textAlign: 'center',
          position: 'relative'
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            color: '#38bdf8',
            padding: '4px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: 600,
            marginBottom: '14px'
          }}>
            <ShieldCheck size={14} /> Vetanco S.A. | SAP S/4HANA Staging
          </div>

          <h1 style={{
            fontSize: '24px',
            fontWeight: 700,
            color: '#ffffff',
            margin: '0 0 6px 0',
            letterSpacing: '-0.02em'
          }}>
            SIAE-Vetanco
          </h1>
          <p style={{
            fontSize: '13px',
            color: '#94a3b8',
            margin: 0,
            lineHeight: 1.4
          }}>
            Sistema Inteligente de Automatización y Extracción de Facturas de Proveedores
          </p>
        </div>

        {/* Cuerpo del formulario */}
        <form onSubmit={handleSubmit} style={{ padding: '32px' }}>
          {error && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '12px 14px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              color: '#991b1b',
              fontSize: '13px'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{error}</div>
            </div>
          )}

          {/* Campo Correo Electrónico */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 600,
              color: '#334155',
              marginBottom: '6px'
            }}>
              Correo Electrónico de Casilla Fiscal
            </label>
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Mail size={18} style={{
                position: 'absolute',
                left: '12px',
                color: '#64748b'
              }} />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ej: facturas.proveedores.franco@gmail.com"
                style={{
                  width: '100%',
                  padding: '11px 12px 11px 38px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  fontSize: '13.5px',
                  color: '#1e293b',
                  transition: 'all 0.2s',
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#1d4ed8';
                  e.target.style.background = '#ffffff';
                  e.target.style.boxShadow = '0 0 0 3px rgba(29, 78, 216, 0.15)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#cbd5e1';
                  e.target.style.background = '#f8fafc';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>
            <p style={{
              fontSize: '11.5px',
              color: '#64748b',
              marginTop: '4px',
              marginBottom: 0
            }}>
              Casilla conectada por IMAP SSL para recepción de comprobantes.
            </p>
          </div>

          {/* Campo Contraseña */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 600,
              color: '#334155',
              marginBottom: '6px'
            }}>
              Contraseña de Acceso
            </label>
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Lock size={18} style={{
                position: 'absolute',
                left: '12px',
                color: '#64748b'
              }} />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="•••••"
                style={{
                  width: '100%',
                  padding: '11px 40px 11px 38px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  fontSize: '13.5px',
                  color: '#1e293b',
                  transition: 'all 0.2s',
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#1d4ed8';
                  e.target.style.background = '#ffffff';
                  e.target.style.boxShadow = '0 0 0 3px rgba(29, 78, 216, 0.15)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#cbd5e1';
                  e.target.style.background = '#f8fafc';
                  e.target.style.boxShadow = 'none';
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Opciones de recordar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '24px'
          }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12.5px',
              color: '#475569',
              cursor: 'pointer',
              userSelect: 'none'
            }}>
              <input
                type="checkbox"
                checked={recordar}
                onChange={(e) => setRecordar(e.target.checked)}
                style={{
                  width: '16px',
                  height: '16px',
                  accentColor: '#1d4ed8',
                  cursor: 'pointer'
                }}
              />
              Recordar credenciales en este equipo
            </label>

            <button
              type="button"
              onClick={autocompletarDemo}
              style={{
                background: 'none',
                border: 'none',
                color: '#1d4ed8',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 6px',
                borderRadius: '4px'
              }}
              title="Carga la casilla de correo oficial y la clave demo (12345)"
            >
              <Key size={12} /> Autocompletar Demo
            </button>
          </div>

          {/* Botón de ingreso */}
          <button
            type="submit"
            disabled={cargando}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: cargando ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 12px rgba(29, 78, 216, 0.3)',
              transition: 'all 0.2s',
              border: 'none'
            }}
          >
            {cargando ? (
              <span>Validando credenciales...</span>
            ) : (
              <>
                <LogIn size={18} /> Iniciar Sesión en SIAE
              </>
            )}
          </button>
        </form>

        {/* Pie con metadatos de seguridad y cátedra */}
        <div style={{
          background: '#f8fafc',
          borderTop: '1px solid #e2e8f0',
          padding: '14px 24px',
          textAlign: 'center',
          fontSize: '11.5px',
          color: '#64748b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px'
        }}>
          <CheckCircle2 size={13} color="#16a34a" /> Control de Acceso RBAC | UADE 2026 — Vetanco S.A.
        </div>
      </div>
    </div>
  );
}
