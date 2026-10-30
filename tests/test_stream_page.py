import unittest
from fastapi.testclient import TestClient
from app.main import app


class StreamPageTests(unittest.TestCase):
    def test_page_and_assets_are_served_without_model_inference(self):
        # No lifespan: these routes do not depend on a translation provider.
        client = TestClient(app)
        response = client.get("/stream")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="practice"', response.text)
        for name in ("stream.mjs", "session.mjs", "style.css"):
            self.assertEqual(client.get("/stream-assets/" + name).status_code, 200)
        self.assertEqual(client.get("/").json()["stream"], "/stream")

    def test_assets_cannot_escape_static_directory(self):
        client = TestClient(app)
        self.assertEqual(client.get("/stream-assets/%2e%2e/main.py").status_code, 404)
