"""Deux appels locaux ; aucun accès réseau et aucun transfert DLQ simulé."""

import base64
import json
import os
from pathlib import Path
from unittest.mock import patch

import main


class LocalRequest:
    method = "POST"

    def __init__(self, event, message_id):
        self.envelope = {"message": {
            "messageId": message_id,
            "data": base64.b64encode(json.dumps(event).encode()).decode(),
        }}

    def get_json(self, silent=True):
        return self.envelope


class LocalBigQuery:
    def insert_rows_json(self, table, rows, row_ids):
        print("Insertion simulée :", json.dumps(rows, ensure_ascii=False))
        return []


if __name__ == "__main__":
    print("DÉMO LOCALE — BigQuery substitué ; Pub/Sub et DLQ non exécutés")
    for name in ("valid", "invalid"):
        event = json.loads((Path(__file__).parent / "examples" / f"{name}-event.json").read_text())
        with patch.dict(os.environ, {"BQ_TABLE": "demo-project.realtime_demo.price_changes"}), patch.object(
            main, "get_client", return_value=LocalBigQuery()
        ):
            body, status = main.pubsub_to_bq(LocalRequest(event, f"local-{name}"))
        print(f"{name}: HTTP {status} — {body}")
