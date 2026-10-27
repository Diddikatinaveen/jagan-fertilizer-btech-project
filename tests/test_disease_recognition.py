import io
import unittest
from unittest.mock import patch

from PIL import Image

from tests.test_support import project


class FakeDiseaseModel:
    input_shape = (None, 224, 224, 3)
    output_shape = (None, 2)

    def __init__(self, prediction):
        self.prediction = prediction
        self.input_values = None

    def predict(self, values, verbose=0):
        self.input_values = values
        return self.prediction


class DiseaseRecognitionTests(unittest.TestCase):
    def setUp(self):
        self.client = project.app.test_client()

    @staticmethod
    def jpeg_bytes(size=(128, 128), color=(90, 150, 70)):
        output = io.BytesIO()
        Image.new("RGB", size, color).save(output, format="JPEG")
        return output.getvalue()

    def upload(self, payload=None, filename="leaf.jpg", crop="paddy", lang="en"):
        data = {
            "crop": crop,
            "lang": lang,
            "image": (io.BytesIO(payload if payload is not None else self.jpeg_bytes()), filename),
        }
        return self.client.post("/api/disease", data=data, content_type="multipart/form-data")

    @staticmethod
    def metadata(threshold=0.65):
        return {
            "schema_version": 1,
            "model_input": {
                "height": 224,
                "width": 224,
                "channels": 3,
                "preprocessing": "rescale_minus1_to1_in_model",
            },
            "output": "softmax_class_probabilities",
            "confidence_threshold": threshold,
            "classes": [
                {
                    "label": "healthy",
                    "crop": "paddy",
                    "health": "healthy",
                    "label_en": "Healthy leaf",
                    "label_te": "ఆరోగ్యకరమైన ఆకు",
                },
                {
                    "label": "leaf_spot",
                    "crop": "paddy",
                    "health": "diseased",
                    "label_en": "Leaf spot",
                    "label_te": "ఆకు మచ్చ",
                },
            ],
            "dataset": {"source": "test fixture", "license": "test", "limitations": "test only"},
            "evaluation": {"test_accuracy": 0.8},
        }

    def test_existing_model_is_explicitly_unavailable(self):
        with patch.object(project, "DISEASE_MODEL", None), patch.object(
            project, "DISEASE_MODEL_METADATA", None
        ):
            status = self.client.get("/api/disease")
            response = self.upload()
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json["model_available"])
        self.assertEqual(status.json["status"], "model_unavailable")
        self.assertEqual(status.json["supported_crops"], [])
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "model_unavailable")

    def test_valid_image_predicts_and_uses_expected_preprocessing_contract(self):
        model = FakeDiseaseModel([[0.9, 0.1]])
        metadata = self.metadata()
        with patch.object(project, "DISEASE_MODEL", model), patch.object(
            project, "DISEASE_MODEL_METADATA", metadata
        ):
            response = self.upload(self.jpeg_bytes(), filename="../../private/leaf.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["prediction"]["label"], "Healthy leaf")
        self.assertEqual(response.json["prediction"]["health"], "healthy")
        self.assertAlmostEqual(response.json["prediction"]["confidence"], 0.9)
        self.assertEqual(model.input_values.shape, (1, 224, 224, 3))
        self.assertGreater(float(model.input_values.min()), 0)
        self.assertLess(float(model.input_values.max()), 255)
        self.assertIn("not a confirmed diagnosis", response.json["disclaimer"])

    def test_low_confidence_returns_inconclusive_result(self):
        model = FakeDiseaseModel([[0.55, 0.45]])
        with patch.object(project, "DISEASE_MODEL", model), patch.object(
            project, "DISEASE_MODEL_METADATA", self.metadata(threshold=0.7)
        ):
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["inconclusive"])
        self.assertIsNone(response.json["prediction"])
        self.assertEqual(response.json["top_predictions"], [])

    def test_unsupported_crop_is_rejected_with_supported_crops(self):
        model = FakeDiseaseModel([[0.9, 0.1]])
        with patch.object(project, "DISEASE_MODEL", model), patch.object(
            project, "DISEASE_MODEL_METADATA", self.metadata()
        ):
            response = self.upload(crop="wheat")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json["code"], "unsupported_crop")
        self.assertEqual(response.json["supported_crops"], ["paddy"])

    def test_malformed_and_spoofed_images_are_rejected(self):
        with patch.object(project, "DISEASE_MODEL", None), patch.object(
            project, "DISEASE_MODEL_METADATA", None
        ):
            corrupt = self.upload(b"not an image", filename="leaf.png")
            wrong_extension = self.upload(self.jpeg_bytes(), filename="leaf.png")
            unsupported = self.upload(self.jpeg_bytes(), filename="leaf.gif")
            dimensions = self.upload(self.jpeg_bytes(size=(32, 32)))
        self.assertEqual(corrupt.json["code"], "invalid_image")
        self.assertEqual(wrong_extension.json["code"], "image_format_mismatch")
        self.assertEqual(unsupported.json["code"], "unsupported_file_type")
        self.assertEqual(dimensions.json["code"], "invalid_image_dimensions")

    def test_oversized_upload_and_global_size_guard_return_safe_json(self):
        too_large = self.upload(b"x" * (5 * 1024 * 1024 + 1))
        global_guard = self.client.post(
            "/api/disease",
            data=b"x" * (5 * 1024 * 1024 + 1024),
            content_type="multipart/form-data",
        )
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(too_large.json["code"], "image_too_large")
        self.assertEqual(global_guard.status_code, 413)
        self.assertEqual(global_guard.json["code"], "image_too_large")

    def test_telugu_prediction_and_disclaimer_are_localized(self):
        model = FakeDiseaseModel([[0.1, 0.9]])
        with patch.object(project, "DISEASE_MODEL", model), patch.object(
            project, "DISEASE_MODEL_METADATA", self.metadata()
        ):
            response = self.upload(lang="te")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["prediction"]["label"], "ఆకు మచ్చ")
        self.assertIn("నిర్ధారిత", response.json["disclaimer"])

    def test_homepage_exposes_localized_disease_screening_controls(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="diseaseForm"', response.data)
        self.assertIn(b'accept=".jpg,.jpeg,.png,image/jpeg,image/png"', response.data)
        with open("static/translations.js", encoding="utf-8") as translations:
            text = translations.read()
        self.assertIn("diseaseDisclaimer", text)
        self.assertIn("diseaseImageTooLarge", text)


if __name__ == "__main__":
    unittest.main()
