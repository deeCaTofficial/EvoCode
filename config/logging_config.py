import logging.config
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import copy

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'fmt': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': '',  # This will be set dynamically
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
}


def setup_logging(log_file_path: Path):
    """
    Настраивает централизованное логирование для приложения.

    Args:
        log_file_path (Path): Путь к файлу логов.
    """
    # Ensure the directory for the log file exists
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    config = copy.deepcopy(LOGGING_CONFIG)
    config['handlers']['file']['filename'] = str(log_file_path)

    logging.config.dictConfig(config)
