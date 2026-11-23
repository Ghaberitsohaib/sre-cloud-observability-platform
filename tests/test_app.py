import json
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

from app.main import SREHandler


class TestSREService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), SREHandler)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_probe(self):
        with urllib.request.urlopen(f"{self.base}/health") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "healthy")

    def test_readiness_probe(self):
        with urllib.request.urlopen(f"{self.base}/ready") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["ready"])

    def test_orders_endpoint(self):
        with urllib.request.urlopen(f"{self.base}/api/orders") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

    def test_chaos_error_and_prometheus_metrics(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base}/simulate/error")
        self.assertEqual(ctx.exception.code, 500)

        with urllib.request.urlopen(f"{self.base}/metrics") as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
            self.assertIn("http_requests_total", body)
            self.assertIn("http_request_errors_total", body)
            self.assertIn("app_sli_availability_ratio", body)
            self.assertIn("app_error_budget_remaining_ratio", body)


if __name__ == "__main__":
    unittest.main()
