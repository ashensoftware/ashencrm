from datetime import datetime

from backend.core.redaction import redact_text

SCRAPE_LOGS = []


def add_scrape_log(message: str):
    """Añade un mensaje al buffer de logs, sin secretos."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    safe_message = redact_text(str(message))
    log_entry = f"[{timestamp }] {safe_message }"
    SCRAPE_LOGS.append(log_entry)
    if len(SCRAPE_LOGS) > 100:
        SCRAPE_LOGS.pop(0)
    print(log_entry, flush=True)


def get_logs():
    """Retorna los logs actuales."""
    return SCRAPE_LOGS
