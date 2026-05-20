import json
import logging
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            log.update(record.extra_fields)
        return json.dumps(log, default=str)


def setup_logging(environment: str = "production") -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO if environment == "production" else logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
        )

    root.handlers.clear()
    root.addHandler(handler)
