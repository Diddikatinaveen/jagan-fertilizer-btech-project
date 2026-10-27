import io
import json
import os
import re
import socket
import unittest
from unittest.mock import patch
from urllib.error import URLError

from tests.test_support import project


class CropAssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.client = project.app.test_client()
        self.client.environ_base["REMOTE_ADDR"] = "192.0.2.10"
        with project.CHAT_RATE_LOCK:
            project.CHAT_RATE_LIMITS.clear()

    def post_question(self, message, lang="en"):
        return self.client.post("/api/chat", json={"message": message, "lang": lang})

    def test_english_fallback_is_identified(self):
        with patch.dict(os.environ, {"CROP_ASSISTANT_API_KEY": ""}):
            with patch("app.urllib.request.urlopen") as mocked:
                response = self.post_question("How should I understand a soil test?")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["mode"], "fallback")
        self.assertEqual(response.json["language"], "en")
        self.assertIn("soil test", response.json["answer"].lower())
        mocked.assert_not_called()

    def test_telugu_is_detected_and_answered_in_telugu(self):
        with patch.dict(os.environ, {"CROP_ASSISTANT_API_KEY": ""}):
            response = self.post_question("వరి ఆకులు పసుపు రంగులోకి మారుతున్నాయి", "en")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["language"], "te")
        self.assertIn("ఆకుల", response.json["answer"])

    def test_empty_and_overlong_questions_are_rejected(self):
        empty = self.post_question("   ")
        too_long = self.post_question("x" * 1001)
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json["code"], "message_required")
        self.assertEqual(too_long.status_code, 400)
        self.assertEqual(too_long.json["code"], "message_too_long")

    def test_invalid_language_and_non_json_are_rejected(self):
        invalid_language = self.post_question("How do I test soil?", "xx")
        invalid_body = self.client.post("/api/chat", data="not json")
        self.assertEqual(invalid_language.status_code, 400)
        self.assertEqual(invalid_language.json["code"], "invalid_language")
        self.assertEqual(invalid_body.status_code, 400)
        self.assertEqual(invalid_body.json["code"], "invalid_request")

    def test_large_request_is_rejected(self):
        response = self.client.post(
            "/api/chat",
            data=json.dumps({"message": "x" * 9000, "lang": "en"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json["code"], "request_too_large")

    def test_ai_provider_response_and_secret_stay_server_side(self):
        provider_response = io.BytesIO(json.dumps({
            "choices": [{"message": {"content": "Check the crop stage and soil report."}}],
        }).encode("utf-8"))
        with patch.dict(os.environ, {
            "CROP_ASSISTANT_API_KEY": "test-provider-secret",
            "CROP_ASSISTANT_MODEL": "test-model",
        }):
            with patch("app.urllib.request.urlopen", return_value=provider_response) as mocked:
                response = self.post_question("How should I understand a soil test?")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["mode"], "ai")
        self.assertEqual(response.json["answer"], "Check the crop stage and soil report.")
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-provider-secret")
        self.assertEqual(mocked.call_args.kwargs["timeout"], project.CHAT_PROVIDER_TIMEOUT_SECONDS)
        self.assertNotIn("test-provider-secret", response.get_data(as_text=True))
        with open("static/app.js", encoding="utf-8") as frontend:
            self.assertNotIn("test-provider-secret", frontend.read())

    def test_provider_failure_and_timeout_return_safe_errors(self):
        with patch.dict(os.environ, {"CROP_ASSISTANT_API_KEY": "server-only-test-key"}):
            with patch("app.urllib.request.urlopen", side_effect=URLError("unavailable")):
                failed = self.post_question("How should I water crops?")
            with patch("app.urllib.request.urlopen", side_effect=socket.timeout()):
                timed_out = self.post_question("How should I water crops?")
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.json["code"], "provider_unavailable")
        self.assertEqual(timed_out.status_code, 504)
        self.assertEqual(timed_out.json["code"], "provider_timeout")
        self.assertNotIn("server-only-test-key", failed.get_data(as_text=True))

    def test_provider_key_is_not_sent_over_remote_http(self):
        with patch.dict(os.environ, {
            "CROP_ASSISTANT_API_KEY": "server-only-test-key",
            "CROP_ASSISTANT_API_URL": "http://provider.example/chat",
        }):
            with patch("app.urllib.request.urlopen") as mocked:
                response = self.post_question("How should I water crops?")
        self.assertEqual(response.status_code, 503)
        mocked.assert_not_called()

    def test_rate_limit_is_enforced(self):
        with patch.object(project, "CHAT_REQUESTS_PER_WINDOW", 1):
            first = self.post_question("What is soil testing?")
            second = self.post_question("What is soil testing?")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json["code"], "rate_limited")

    def test_existing_storefront_and_access_controls_remain_available(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'id="assistantForm"', home.data)
        self.assertIn(b'href="#cropAssistant"', home.data)
        self.assertIn(b'id="cartDialog"', home.data)
        csrf = re.search(rb'<meta name="csrf-token" content="([^"]+)"', home.data).group(1).decode()
        self.assertEqual(self.client.get("/api/products").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/register").status_code, 200)
        self.assertEqual(self.client.get("/admin/login").status_code, 200)
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.assertEqual(self.client.get("/api/account/orders").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/products").status_code, 401)
        checkout = self.client.post(
            "/api/orders",
            json={},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(checkout.status_code, 400)
        self.assertEqual(checkout.json["code"], "invalid_customer_details")


if __name__ == "__main__":
    unittest.main()
