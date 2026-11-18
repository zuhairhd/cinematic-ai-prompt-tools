import copy
import io
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core

EXAMPLE = Path(__file__).resolve().parents[1] / "example_project.json"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.project = core.load_project(EXAMPLE)
        self.analysis = self.project["analysis"]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def image(self):
        path = self.folder / "portrait.png"
        Image.new("RGBA", (120, 160), (30, 40, 50, 0)).save(path)
        return core.prepare_image(path)

    def test_every_field_included_in_prompt(self):
        text = core.build_prompt(self.analysis)
        self.assertEqual(len(core.FIELDS), 33)
        for row in self.analysis["fields"].values():
            self.assertIn(row["choice"].rstrip("."), text)
        self.assertNotIn("--ar", text)

    def test_midjourney_ratio_and_raw(self):
        text = core.build_prompt(self.analysis, "2.39:1", "Midjourney")
        self.assertTrue(text.endswith("--ar 239:100 --raw"))
        self.assertNotIn("--sref", text)

    def test_missing_fields_fail_instead_of_template_fallback(self):
        del self.analysis["fields"]["fill"]
        with self.assertRaisesRegex(core.StudioError, "Incomplete shot plan"):
            core.build_prompt(self.analysis)

    def test_empty_and_auto_choices_rejected(self):
        for invalid in ("", "auto", "TBD", "not applicable"):
            candidate = copy.deepcopy(self.analysis)
            candidate["fields"]["lens"]["choice"] = invalid
            with self.assertRaises(core.StudioError):
                core.validate_analysis(candidate)

    def test_estimate_cannot_be_labeled_observed(self):
        self.analysis["fields"]["aperture"]["basis"] = "observed"
        validated = core.validate_analysis(self.analysis)
        self.assertEqual(validated["fields"]["aperture"]["basis"], "inferred")

    def test_camera_settings_require_explicit_numbers_and_units(self):
        for key in ("lens", "distance", "aperture", "shutter", "iso", "white_balance", "key_temperature"):
            candidate = copy.deepcopy(self.analysis)
            candidate["fields"][key]["choice"] = "Use a pleasant natural photographic look."
            with self.assertRaisesRegex(core.StudioError, "numeric setting"):
                core.validate_analysis(candidate)

    def test_auto_setting_embedded_in_sentence_is_rejected(self):
        self.analysis["fields"]["white_balance"]["choice"] = "Use auto white balance near 5000 K."
        with self.assertRaisesRegex(core.StudioError, "automatic"):
            core.validate_analysis(self.analysis)

    def test_explicit_absence_is_valid(self):
        self.analysis["fields"]["rim"]["choice"] = "No separate rim light; use only the broad key spill."
        core.validate_analysis(self.analysis)

    def test_user_edit_propagates_to_prompt_and_evidence(self):
        self.analysis["fields"]["lens"].update(choice="Use a 50 mm lens with neutral optical rendering.", basis="user")
        self.assertIn("50 mm", core.build_prompt(self.analysis))
        self.assertIn("[user]", core.build_evidence(self.analysis))

    def test_project_roundtrip_does_not_export_secrets(self):
        path = self.folder / "project.json"
        opts = {**self.project["options"], "api_key": "DO_NOT_SAVE", "token": "SECRET"}
        core.save_project(path, self.analysis, opts,
                          {"filename": "face.jpg", "full_path": "PRIVATE_PATH", "bytes": "IMAGE_BYTES"},
                          {"provider": "OpenAI", "api_key": "NO_KEY"})
        loaded = core.load_project(path)
        self.assertEqual(loaded["analysis"], self.analysis)
        for secret in ("DO_NOT_SAVE", "SECRET", "PRIVATE_PATH", "IMAGE_BYTES", "NO_KEY"):
            self.assertNotIn(secret, path.read_text())

    def test_bad_project_is_rejected(self):
        for data in ({"version": 9}, {**self.project, "options": {"ratio": "weird"}}):
            path = self.folder / "bad.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(core.StudioError):
                core.load_project(path)

    def test_image_resized_oriented_and_exif_removed(self):
        image = Image.new("RGB", (2400, 1200), (64, 90, 120))
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "PRIVATE_AUTHOR"
        path = self.folder / "rotated.jpg"
        image.save(path, exif=exif)
        prepared = core.prepare_image(path)
        self.assertEqual(prepared.metadata["original_size"], [1200, 2400])
        self.assertEqual(prepared.preview.size, (800, 1600))
        decoded = Image.open(io.BytesIO(prepared.jpeg))
        self.assertFalse(decoded.getexif())
        self.assertNotIn(b"PRIVATE_AUTHOR", prepared.jpeg)

    def test_transparent_image_has_intentional_background(self):
        prepared = self.image()
        self.assertEqual(prepared.preview.mode, "RGB")
        self.assertEqual(prepared.preview.getpixel((0, 0)), (240, 240, 240))

    def test_corrupt_image_is_reported(self):
        path = self.folder / "bad.jpg"
        path.write_bytes(b"not an image")
        with self.assertRaises(core.StudioError):
            core.prepare_image(path)

    def test_local_endpoint_rejects_remote_and_credentials(self):
        for url in ("https://example.com", "file:///etc/passwd", "http://user:pass@localhost", "http://localhost:11434/api", "http://localhost:BAD"):
            with self.assertRaises(core.StudioError):
                core.local_endpoint(url)
        self.assertEqual(core.local_endpoint("http://127.0.0.1:11434/"), "http://127.0.0.1:11434")

    def test_schema_requires_all_fields_and_forbids_extras(self):
        schema = core.make_schema()
        self.assertEqual(set(schema["properties"]["fields"]["required"]), set(core.FIELDS))
        self.assertFalse(schema["additionalProperties"])

    def openai_response(self):
        return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(self.analysis)}]}], "usage": {"total_tokens": 100}}

    def test_openai_payload_has_real_image_and_strict_schema(self):
        with patch("core.request_json", return_value=self.openai_response()) as request:
            result, usage = core.analyze_image(self.image(), "OpenAI", "gpt-4.1", api_key="test-key", brief="Keep warm light")
        args = request.call_args.args
        payload = args[1]
        self.assertEqual(args[0], "https://api.openai.com/v1/responses")
        self.assertFalse(payload["store"])
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertTrue(payload["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(result, self.analysis)

    def test_provider_refusal_and_incomplete_are_not_success(self):
        for response in ({"status": "incomplete", "output": []},
                         {"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}):
            with self.assertRaises(core.StudioError):
                core.extract_openai(response)

    def test_invalid_json_rejected(self):
        response = self.openai_response()
        response["output"][0]["content"][0]["text"] = "not json"
        with patch("core.request_json", return_value=response), self.assertRaises(core.StudioError):
            core.analyze_image(self.image(), "OpenAI", "gpt-4.1", api_key="test")

    def test_ollama_image_schema_and_local_preflight(self):
        response = {"done": True, "done_reason": "stop", "message": {"content": json.dumps(self.analysis)}}
        with patch("core.request_json", side_effect=[{"capabilities": ["vision", "completion"]}, response]) as request:
            result, _ = core.analyze_image(self.image(), "Ollama (local)", "vision-model")
        self.assertEqual(result, self.analysis)
        self.assertEqual(request.call_args_list[0].args[0], "http://localhost:11434/api/show")
        payload = request.call_args_list[1].args[1]
        self.assertTrue(payload["messages"][1]["images"])
        self.assertEqual(set(payload["format"]["required"]), {"summary", "fields", "avoid", "uncertainties"})

    def test_ollama_remote_and_text_only_models_rejected(self):
        for metadata in ({"remote_host": "remote.example"}, {"capabilities": ["completion"]}):
            with patch("core.request_json", return_value=metadata), self.assertRaises(core.StudioError):
                core.analyze_image(self.image(), "Ollama (local)", "test-model")

    def test_http_transport_and_error_hygiene(self):
        received = {}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received["auth"] = self.headers.get("Authorization")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            def do_GET(self):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'SECRET_FROM_PROVIDER')
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            self.assertTrue(core.request_json(url, {"example": 1}, "test-key")["ok"])
            self.assertEqual(received, {"body": {"example": 1}, "auth": "Bearer test-key"})
            with self.assertRaises(core.StudioError) as caught:
                core.request_json(url)
            self.assertIn("401", str(caught.exception))
            self.assertNotIn("SECRET", str(caught.exception))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
