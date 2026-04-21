import structlog
import logging
import sys
from asgi_correlation_id.context import correlation_id

SENSITIVE_KEYS = {
    "password", 
    "access_token", 
    "authorization", 
    "credentials", 
    "code", 
    "csrf_token",
    "refresh_token",
    "client_secret",
    "id_token",
}

def redact_secrets(logger, log_method, event_dict):
    """Structlog processor to redact sensitive values from logs."""
    for key in event_dict.keys():
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict

def setup_logging():
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_secrets,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    logger = structlog.get_logger(name)
    cid = correlation_id.get()
    if cid:
        return logger.bind(correlation_id=cid)
    return logger
