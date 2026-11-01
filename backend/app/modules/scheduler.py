"""
Planificador de Tareas en Segundo Plano (Scheduler Background Worker)
[RF-02, RF-25]
1. Polling de correos cada 2 horas (configurable por variable de entorno).
2. Cron diario de generación automática de lote SAP a las 17:00 hs (días hábiles).
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.models import TipoDisparoBatch
from app.modules.mail_ingestor import ejecutar_ingesta_automatica
from app.modules.batch_exporter import generar_lote_batch_sap

logger = logging.getLogger("siae.scheduler")

scheduler = BackgroundScheduler()


def job_escanear_correos():
    """[RF-02] Tarea recurrente de polling de casilla de correo o bandeja local."""
    logger.info("Scheduler: Ejecutando escaneo programado de correos entrantes...")
    db = SessionLocal()
    try:
        resultado = ejecutar_ingesta_automatica(db)
        logger.info(f"Scheduler escaneo finalizado: {resultado}")
    except Exception as e:
        logger.error(f"Error en job_escanear_correos: {e}")
    finally:
        db.close()


def job_cierre_batch_diario():
    """[RF-25] Cron Job diario a las 17:00 hs (lunes a viernes) para consolidación de lote SAP."""
    logger.info("Scheduler: Ejecutando cierre automático de Lote Batch SAP (17:00 hs)...")
    db = SessionLocal()
    try:
        ok, msg, lote = generar_lote_batch_sap(db, tipo_disparo=TipoDisparoBatch.CRON)
        logger.info(f"Scheduler lote finalizado: {msg}")
    except Exception as e:
        logger.error(f"Error en job_cierre_batch_diario: {e}")
    finally:
        db.close()


def iniciar_scheduler():
    """Inicia el planificador de tareas en segundo plano."""
    if scheduler.running:
        return

    # 1. Polling cada 2 horas (RF-02)
    scheduler.add_job(
        job_escanear_correos,
        trigger=IntervalTrigger(hours=2),
        id="job_escanear_correos",
        name="Escaneo periódico de casilla de correo",
        replace_existing=True
    )

    # 2. Consolidación Batch SAP a las 17:00 hs de lunes a viernes (RF-25)
    scheduler.add_job(
        job_cierre_batch_diario,
        trigger=CronTrigger(
            hour=settings.BATCH_CRON_HOUR,
            minute=settings.BATCH_CRON_MINUTE,
            day_of_week="mon-fri"
        ),
        id="job_cierre_batch_diario",
        name="Cierre diario y exportación Batch SAP 17:00 hs",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler iniciado con éxito (Polling cada 2h + Cierre Batch 17:00hs).")


def detener_scheduler():
    """Detiene el planificador."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido.")
