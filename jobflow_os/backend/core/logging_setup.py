"""
Central logging setup for JobFlow OS.
Call setup_logging() once at startup (from main.py).

Log format:
  2026-03-15 20:45:12 | INFO     | LinkedInAgent.read_profile   | [agent_1] Loading Sarah Kim
  2026-03-15 20:45:13 | ERROR    | contact_agent.send_invite    | [agent_1] Guard FAILED → captcha_detected

Log file: logs/jobflow.log  (rotates at 5MB, keeps 5 backups)
"""
import logging
import logging.handlers
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent.parent / 'logs'
LOG_FILE = LOG_DIR / 'jobflow.log'

_setup_done = False


class _PaddedFormatter(logging.Formatter):
    """Formats log records with fixed-width component column for easy reading."""
    def format(self, record):
        # Pad the logger name to 30 chars so columns align
        record.name = record.name[:32].ljust(32)
        return super().format(record)


def setup_logging(level: int = logging.DEBUG):
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt = _PaddedFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ── File handler (rotating, 5MB × 5 backups) ──
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # ── Console handler (INFO+ only, keeps terminal clean) ──
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    # ── Root logger ──
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Silence noisy third-party loggers
    for noisy in ('selenium', 'urllib3', 'httpx', 'httpcore',
                  'undetected_chromedriver', 'websockets', 'asyncio'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger('jobflow').info('Logging initialised → %s', LOG_FILE)
