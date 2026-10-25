"""Adaptateur HTTP pour Functions Framework ; version reconstruite pour ce dépôt."""

import json
import logging
import os
from functools import lru_cache

from price_events import InvalidEvent, process_envelope

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False


@lru_cache(maxsize=1)
def get_client():
    # Aucun accès aux identifiants ni import du SDK pendant les tests hors ligne.
    from google.cloud import bigquery

    return bigquery.Client()


def pubsub_to_bq(request):
    if request.method != "POST":
        return "Method Not Allowed", 405
    try:
        message_id = process_envelope(
            request.get_json(silent=True), os.environ.get("BQ_TABLE"), get_client
        )
    except InvalidEvent as error:
        logger.warning(json.dumps({"event": "invalid_message", "reason": str(error)}))
        return "Invalid message", 500
    except Exception as error:
        # Ne pas journaliser le contenu métier ou le texte brut d'une erreur SDK.
        logger.error(json.dumps({"event": "processing_failed", "error_type": type(error).__name__}))
        return "Processing failed", 500
    logger.info(json.dumps({"event": "processed_price_change", "message_id": message_id}))
    return "OK", 200
