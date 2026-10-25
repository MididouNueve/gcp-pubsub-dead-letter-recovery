"""Reproduction pédagogique : contrat de message et insertion, sans SDK à l'import."""

import base64
import binascii
import json
import math
import re
from datetime import datetime, timezone


class InvalidEvent(ValueError):
    """Événement inexploitable ; le push doit échouer pour rejoindre la DLQ."""


class WriteFailed(RuntimeError):
    """BigQuery a renvoyé des erreurs par ligne."""


def decode_event(envelope):
    if not isinstance(envelope, dict) or not isinstance(envelope.get("message"), dict):
        raise InvalidEvent("missing_message")
    message = envelope["message"]
    message_id = message.get("messageId")
    if not isinstance(message_id, str) or not message_id.strip():
        raise InvalidEvent("missing_message_id")
    encoded = message.get("data")
    if not isinstance(encoded, str):
        raise InvalidEvent("missing_data")
    try:
        event = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeError) as error:
        raise InvalidEvent("invalid_encoding_or_json") from error
    if not isinstance(event, dict):
        raise InvalidEvent("expected_object")
    required = {"event_type", "product_id", "old_price", "new_price", "timestamp"}
    if required - event.keys():
        raise InvalidEvent("missing_fields")
    if event["event_type"] != "price_change":
        raise InvalidEvent("unexpected_event_type")
    if not isinstance(event["product_id"], str) or not event["product_id"].strip():
        raise InvalidEvent("invalid_product_id")
    prices = {}
    for field in ("old_price", "new_price"):
        value = event[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidEvent("invalid_price_type")
        try:
            price = float(value)
        except (ValueError, OverflowError) as error:
            raise InvalidEvent("invalid_price") from error
        if not math.isfinite(price) or price < 0:
            raise InvalidEvent("invalid_price")
        prices[field] = price
    timestamp = event["timestamp"]
    if not isinstance(timestamp, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
        timestamp,
    ):
        raise InvalidEvent("invalid_timestamp")
    try:
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        timestamp = timestamp.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError) as error:
        raise InvalidEvent("invalid_timestamp") from error
    return message_id, {"product_id": event["product_id"], **prices, "ts": timestamp}


def process_envelope(envelope, table_id, client_factory):
    message_id, row = decode_event(envelope)
    if not isinstance(table_id, str) or not re.fullmatch(
        r"[a-z][a-z0-9-]+\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", table_id
    ):
        raise ValueError("BQ_TABLE must be project.dataset.table")
    client = client_factory()
    errors = client.insert_rows_json(table_id, [row], row_ids=[message_id])
    if errors:
        raise WriteFailed("bigquery_row_errors")
    return message_id
