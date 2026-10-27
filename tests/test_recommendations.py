import io
import json
import os
import unittest
from unittest.mock import patch

from test_support import project


class ProductRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.client = project.app.test_client()
        self.client.environ_base["REMOTE_ADDR"] = "192.0.2.20"
        with project.RECOMMENDATION_RATE_LOCK:
            project.RECOMMENDATION_RATE_LIMITS.clear()
        with project.app.app_context():
            self.fixture_products = [
                project.Product(
                    name="Recommendation Test Nitrogen",
                    category="Fertilizers",
                    description="Nitrogen fertilizer listing for matching tests.",
                    price=123.45,
                    unit="pack",
                    stock=4,
                    guidance_en="Check soil-test results and the product label.",
                    guidance_te="నేల పరీక్ష ఫలితాలు, ఉత్పత్తి లేబుల్ పరిశీలించండి.",
                    active=True,
                    price_verified=True,
                ),
                project.Product(
                    name="Inactive Recommendation Nitrogen",
                    category="Fertilizers",
                    description="Nitrogen fertilizer listing.",
                    price=99,
                    stock=5,
                    active=False,
                    price_verified=True,
                ),
                project.Product(
                    name="Sold Out Recommendation Nitrogen",
                    category="Fertilizers",
                    description="Nitrogen fertilizer listing.",
                    price=99,
                    stock=0,
                    active=True,
                    price_verified=True,
                ),
                project.Product(
                    name="Restricted Test Product",
                    category="Pesticides",
                    description="Nitrogen crop protection product.",
                    price=99,
                    stock=5,
                    active=True,
                    registration_verified=True,
                ),
                project.Product(
                    name="Unverified Price Nitrogen",
                    category="Fertilizers",
                    description="Nitrogen fertilizer listing.",
                    price=999,
                    stock=3,
                    active=True,
                    price_verified=False,
                ),
            ]
            project.db.session.add_all(self.fixture_products)
            project.db.session.commit()
            self.fixture_ids = {product.id for product in self.fixture_products}
            self.active_id = self.fixture_products[0].id

    def tearDown(self):
        with project.app.app_context():
            project.Product.query.filter(project.Product.id.in_(self.fixture_ids)).delete(
                synchronize_session=False
            )
            project.db.session.commit()

    def payload(self, **overrides):
        data = {
            "crop": "paddy",
            "stage": "vegetative",
            "location": "Guntur",
            "soil": "Low nitrogen; pH 6.5",
            "question": "Which fertilizer listings mention nitrogen for review?",
            "lang": "en",
        }
        data.update(overrides)
        return data

    def recommend(self, **overrides):
        with patch.dict(os.environ, {"CROP_ASSISTANT_API_KEY": ""}):
            return self.client.post("/api/recommend", json=self.payload(**overrides))

    def test_paddy_vegetative_matches_database_nutrient_listings(self):
        response = self.recommend()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["mode"], "rule_based")
        self.assertEqual(response.json["language"], "en")
        ids = {product["id"] for product in response.json["products"]}
        self.assertIn(self.active_id, ids)
        excluded_ids = {product.id for product in self.fixture_products[1:4]}
        self.assertTrue(ids.isdisjoint(excluded_ids))
        unverified_price_id = self.fixture_products[4].id
        self.assertIn(unverified_price_id, ids)
        self.assertIn("not a confirmed crop prescription", response.json["disclaimer"])
        matched = next(product for product in response.json["products"] if product["id"] == self.active_id)
        with project.app.app_context():
            product = project.db.session.get(project.Product, self.active_id)
            self.assertEqual(matched["name"], product.name)
            self.assertEqual(matched["description"], product.description)
            self.assertEqual(matched["price"], product.price)
            self.assertTrue(matched["price_verified"])
            self.assertEqual(matched["stock"], product.stock)
            self.assertIn("not", matched["reason"].lower())
        unverified_price = next(
            item for item in response.json["products"] if item["id"] == unverified_price_id
        )
        self.assertIsNone(unverified_price["price"])
        self.assertFalse(unverified_price["price_verified"])

    def test_seed_match_requires_sowing_stage_and_crop_name(self):
        response = self.recommend(
            stage="sowing",
            soil="",
            question="Are paddy seeds listed for review?",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Paddy Seeds",
            {product["name"] for product in response.json["products"]},
        )
        vegetative = self.recommend(
            stage="vegetative",
            soil="",
            question="Are paddy seeds listed for review?",
        )
        self.assertNotIn(
            "Paddy Seeds",
            {product["name"] for product in vegetative.json["products"]},
        )

    def test_different_and_unknown_crops_do_not_inherit_unverified_suitability(self):
        wheat = self.recommend(
            crop="wheat",
            soil="",
            question="Which products could suit this wheat crop?",
        )
        unknown = self.recommend(
            crop="other",
            other_crop="dragon fruit",
            soil="",
            question="What catalogue options are available?",
        )
        self.assertEqual(wheat.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(wheat.json["products"], [])
        self.assertEqual(unknown.json["products"], [])

    def test_soil_information_can_match_and_empty_match_is_helpful(self):
        soil_match = self.recommend(
            soil="Low nitrogen in soil report",
            question="What nutrient listings should I review?",
        )
        no_match = self.recommend(
            soil="",
            question="Can you help me with my farm?",
            crop="cotton",
        )
        self.assertIn(self.active_id, {item["id"] for item in soil_match.json["products"]})
        self.assertEqual(no_match.json["products"], [])
        self.assertIn("soil-test", no_match.json["disclaimer"])

    def test_telugu_result_reason_and_disclaimer_are_localized(self):
        response = self.recommend(
            soil="నేలలో నత్రజని తక్కువ",
            question="ఎరువు జాబితాలో ఏమి ఉంది?",
            lang="te",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["language"], "te")
        self.assertIn("నేల పరీక్ష", response.json["disclaimer"])
        self.assertTrue(any("జాబితా" in item["reason"] for item in response.json["products"]))

    def test_validation_rejects_bad_fields_and_large_input(self):
        missing_other = self.recommend(crop="other", other_crop="")
        bad_stage = self.recommend(stage="tillering")
        missing_question = self.recommend(question="  ")
        too_long = self.recommend(question="x" * 1001)
        invalid_json = self.client.post("/api/recommend", data="bad body")
        self.assertEqual(missing_other.json["code"], "other_crop_required")
        self.assertEqual(bad_stage.json["code"], "invalid_stage")
        self.assertEqual(missing_question.json["code"], "question_required")
        self.assertEqual(too_long.json["code"], "input_too_long")
        self.assertEqual(invalid_json.json["code"], "invalid_request")

    def test_ai_provider_can_only_rank_database_candidates(self):
        provider_response = io.BytesIO(json.dumps({
            "choices": [{"message": {"content": json.dumps({"ids": [self.active_id]})}}],
        }).encode("utf-8"))
        with patch.dict(os.environ, {
            "CROP_ASSISTANT_API_KEY": "recommendation-provider-test-key",
            "CROP_ASSISTANT_MODEL": "test-model",
        }):
            with patch("app.urllib.request.urlopen", return_value=provider_response) as mocked:
                response = self.client.post("/api/recommend", json=self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["mode"], "ai")
        self.assertEqual([item["id"] for item in response.json["products"]], [self.active_id])
        self.assertEqual(response.json["products"][0]["name"], "Recommendation Test Nitrogen")
        request_payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        user_content = request_payload["messages"][1]["content"]
        self.assertNotIn("Guntur", user_content)
        self.assertNotIn("Low nitrogen; pH 6.5", user_content)
        self.assertNotIn("Which fertilizer listings mention nitrogen for review?", user_content)
        self.assertNotIn("recommendation-provider-test-key", response.get_data(as_text=True))

    def test_ai_cannot_return_non_catalogue_product_ids(self):
        provider_response = io.BytesIO(json.dumps({
            "choices": [{"message": {"content": '{"ids":[999999999]}'}}],
        }).encode("utf-8"))
        with patch.dict(os.environ, {
            "CROP_ASSISTANT_API_KEY": "recommendation-provider-test-key",
        }):
            with patch("app.urllib.request.urlopen", return_value=provider_response):
                response = self.client.post("/api/recommend", json=self.payload())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "provider_unavailable")

    def test_recommendation_endpoint_has_its_own_rate_limit(self):
        with patch.object(project, "RECOMMENDATION_REQUESTS_PER_WINDOW", 1):
            first = self.recommend()
            second = self.recommend()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json["code"], "rate_limited")


if __name__ == "__main__":
    unittest.main()
