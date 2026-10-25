import base64
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import main
from price_events import InvalidEvent, decode_event

VALID = json.loads((Path(__file__).resolve().parents[1] / "examples/valid-event.json").read_text())
TABLE = "demo-project.realtime_demo.price_changes"


def envelope(event):
    return {"message": {"messageId": "test-123", "data": base64.b64encode(json.dumps(event).encode()).decode()}}


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.insert_rows_json.return_value = []
        self.factory = patch.object(main, "get_client", return_value=self.client).start()
        patch.dict(os.environ, {"BQ_TABLE": TABLE}).start()
        self.addCleanup(patch.stopall)

    def call(self, body, method="POST"):
        request = Mock(method=method)
        request.get_json.return_value = body
        return main.pubsub_to_bq(request)

    def test_valid_message_writes_expected_row_then_acknowledges(self):
        self.assertEqual(self.call(envelope(VALID)), ("OK", 200))
        self.client.insert_rows_json.assert_called_once_with(TABLE, [{
            "product_id": "DEMO-001", "old_price": 10.0,
            "new_price": 9.5, "ts": "2026-10-25T12:00:00+00:00",
        }], row_ids=["test-123"])

    def test_missing_fields_fail_without_creating_client(self):
        for field in ("old_price", "new_price", "timestamp", "product_id", "event_type"):
            with self.subTest(field=field):
                event = copy.deepcopy(VALID)
                del event[field]
                self.assertEqual(self.call(envelope(event))[1], 500)
        self.factory.assert_not_called()

    def test_malformed_envelopes_fail_without_write(self):
        for body in (None, [], {}, {"message": None}, {"message": {}},
                     {"message": {"messageId": "test", "data": "%%%"}},
                     {"message": {"messageId": "test", "data": "bm90LWpzb24="}}):
            with self.subTest(body=body):
                self.assertEqual(self.call(body)[1], 500)
        self.factory.assert_not_called()

    def test_json_array_is_not_an_event(self):
        self.assertEqual(self.call(envelope([]))[1], 500)
        self.factory.assert_not_called()

    def test_invalid_prices_are_rejected(self):
        for value in (True, None, "10.0", -1, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assertEqual(self.call(envelope({**VALID, "old_price": value}))[1], 500)
        self.factory.assert_not_called()

    def test_invalid_timestamps_are_rejected(self):
        for value in (None, "2026-10-25", "2026-10-25T12:00:00", "2026-02-30T12:00:00Z"):
            with self.subTest(value=value):
                with self.assertRaises(InvalidEvent):
                    decode_event(envelope({**VALID, "timestamp": value}))

    def test_timezone_is_normalized(self):
        _, row = decode_event(envelope({**VALID, "timestamp": "2026-10-25T14:00:00+02:00"}))
        self.assertEqual(row["ts"], "2026-10-25T12:00:00+00:00")

    def test_wrong_event_type_and_blank_product_are_rejected(self):
        for event in ({**VALID, "event_type": "stock_change"}, {**VALID, "product_id": " "}):
            self.assertEqual(self.call(envelope(event))[1], 500)
        self.factory.assert_not_called()

    def test_bigquery_exception_does_not_acknowledge(self):
        self.client.insert_rows_json.side_effect = PermissionError("denied")
        self.assertEqual(self.call(envelope(VALID))[1], 500)

    def test_bigquery_row_errors_do_not_acknowledge(self):
        self.client.insert_rows_json.return_value = [{"index": 0, "errors": [{"reason": "invalid"}]}]
        self.assertEqual(self.call(envelope(VALID))[1], 500)

    def test_invalid_table_config_prevents_write(self):
        with patch.dict(os.environ, {"BQ_TABLE": "dataset.table"}):
            self.assertEqual(self.call(envelope(VALID))[1], 500)
        self.factory.assert_not_called()

    def test_repeated_delivery_reuses_insert_id_without_claiming_dedup(self):
        self.call(envelope(VALID))
        self.call(envelope(VALID))
        self.assertEqual(self.client.insert_rows_json.call_count, 2)
        self.assertEqual([c.kwargs["row_ids"] for c in self.client.insert_rows_json.call_args_list],
                         [["test-123"], ["test-123"]])

    def test_get_does_not_write(self):
        self.assertEqual(self.call(None, "GET")[1], 405)
        self.factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
