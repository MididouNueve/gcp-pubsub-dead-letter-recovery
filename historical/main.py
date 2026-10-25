# Transcription de la capture 11, via la synthèse historique jointe.
# Ce fichier ne constitue pas le source original ni une version déployée vérifiée.
import base64
import json
from flask import Request
from google.cloud import bigquery

bq = bigquery.Client()
TABLE_ID = "realtime_demo.price_changes"


def pubsub_to_bq(request: Request):
    try:
        envelope = request.get_json(silent=True)

        if not envelope or "message" not in envelope:
            raise ValueError(
                "Invalid Pub/Sub push message: no 'message' field"
            )

        message = envelope["message"]

        if "data" not in message:
            raise ValueError("Pub/Sub message missing 'data'")

        data = base64.b64decode(
            message["data"]
        ).decode("utf-8")

        parsed = json.loads(data)

        row = {
            "product_id": parsed["product_id"],
            "old_price": float(parsed["old_price"]),
            "new_price": float(parsed["new_price"]),
            "ts": parsed["timestamp"],
        }

        errors = bq.insert_rows_json(TABLE_ID, [row])

        if errors:
            raise RuntimeError(errors)

        return ("OK", 200)

    except Exception as e:
        print("ERROR:", e)
        return ("BAD", 500)
