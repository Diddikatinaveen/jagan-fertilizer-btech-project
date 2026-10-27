import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

from tests.test_support import project


EXPECTED_DEMO_PRICES = {
    "Urea": (300, "45 kg bag"),
    "DAP": (1350, "50 kg bag"),
    "NPK 28-28-0": (1600, "50 kg bag"),
    "Paddy Seeds": (500, "5 kg pack"),
    "Micronutrient Fertilizer (Sample Pack)": (250, "Sample pack"),
}

EXPECTED_CATALOGUE_NAMES = {
    "Urea",
    "DAP",
    "NPK 28-28-0",
    "Other NPK Fertilizer Grades",
    "Organic Manure and Compost",
    "Micronutrient Fertilizer (Sample Pack)",
    "Paddy Seeds",
    "Wheat Seeds",
    "Vegetable Seeds",
    "Biofertilizer",
    "Soil Improvement Product",
}


class CatalogueSeedTests(unittest.TestCase):
    def setUp(self):
        self.test_client = project.app.test_client()
        self.product_name = f"Catalogue Workflow Fertilizer {uuid.uuid4().hex[:8]}"
        with project.app.app_context():
            product = project.Product(
                name=self.product_name,
                category="Fertilizers",
                description="Catalogue fixture.",
                price=20,
                unit="test pack",
                stock=3,
                active=True,
                price_verified=True,
            )
            project.db.session.add(product)
            project.db.session.commit()
            self.product_id = product.id

    def tearDown(self):
        with project.app.app_context():
            product = project.db.session.get(project.Product, self.product_id)
            if product:
                project.db.session.delete(product)
                project.db.session.commit()

    def test_seed_is_idempotent_preserves_shop_values_and_images_resolve(self):
        project_root = Path(__file__).resolve().parents[1]
        seed_script = project_root / "seed_products.py"
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "catalogue-test.db"
            environment = os.environ.copy()
            environment["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
            environment["APP_ENV"] = "development"

            def run_seed():
                return subprocess.run(
                    [sys.executable, str(seed_script)],
                    cwd=project_root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=True,
                )

            first = run_seed()
            self.assertIn("Catalogue seed complete", first.stdout)

            connection = sqlite3.connect(database_path)
            try:
                seeded_count = connection.execute(
                    "SELECT COUNT(*) FROM product"
                ).fetchone()[0]
                rows = connection.execute(
                    "SELECT name, category, price, unit, stock, image, stock_verified, "
                    "description, description_te, brand, is_demo_price, price_verified "
                    "FROM product WHERE category != 'Pesticides'"
                ).fetchall()
                products = {row[0]: row for row in rows}
                self.assertEqual(set(products), EXPECTED_CATALOGUE_NAMES)

                for name, (price, unit) in EXPECTED_DEMO_PRICES.items():
                    row = products[name]
                    self.assertEqual(row[2], price)
                    self.assertEqual(row[3], unit)
                    self.assertEqual(row[10], 1)
                    self.assertEqual(row[11], 0)
                    self.assertTrue(row[7])
                    self.assertTrue(row[8])
                    self.assertFalse(row[9])

                with project.app.test_client() as client:
                    for row in rows:
                        image_url = f"/static/{row[5]}"
                        response = client.get(image_url)
                        self.assertEqual(response.status_code, 200, image_url)
                        self.assertEqual(response.mimetype, "image/svg+xml")
                        response.close()
                self.assertTrue(all(row[6] == 0 for row in rows if row[4] == 0))

                connection.execute(
                    "UPDATE product SET price = 999, price_verified = 1, "
                    "is_demo_price = 0, stock = 7 WHERE name = 'Urea'"
                )
                connection.execute(
                    'INSERT INTO "order" '
                    "(order_reference, customer_name, phone, address, notes, items_json, total, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("JF-SEED-TEST", "Test Farmer", "9876543210", "Test address", "", "[]", 0, "Received"),
                )
                connection.commit()
                order_count = connection.execute(
                    'SELECT COUNT(*) FROM "order"'
                ).fetchone()[0]
            finally:
                connection.close()

            second = run_seed()
            self.assertIn("Catalogue seed complete", second.stdout)

            connection = sqlite3.connect(database_path)
            try:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM product").fetchone()[0],
                    seeded_count,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT price, price_verified, is_demo_price, stock "
                        "FROM product WHERE name = 'Urea'"
                    ).fetchone(),
                    (999.0, 1, 0, 7),
                )
                self.assertEqual(
                    connection.execute('SELECT COUNT(*) FROM "order"').fetchone()[0],
                    order_count,
                )
            finally:
                connection.close()

    def test_demo_price_api_exposes_notice_but_checkout_rejects_it(self):
        with project.app.app_context():
            product = project.db.session.get(project.Product, self.product_id)
            product.price = 300
            product.price_verified = False
            product.is_demo_price = True
            project.db.session.commit()

        listing = self.test_client.get(f"/api/products?search={self.product_name.replace(' ', '%20')}")
        self.assertEqual(listing.status_code, 200)
        item = next(row for row in listing.json if row["name"] == self.product_name)
        self.assertEqual(item["price"], 300)
        self.assertTrue(item["is_demo_price"])
        self.assertFalse(item["price_verified"])

        token = self.csrf_token()
        response = self.test_client.post(
            "/api/orders",
            json={
                "name": "Demo Price Test",
                "phone": "9876543210",
                "address": "Test address",
                "items": [{"id": self.product_id, "quantity": 1}],
            },
            headers={"X-CSRF-Token": token},
        )
        self.assertNotEqual(response.status_code, 201)
        self.assertIn(response.json["code"], {"price_unavailable", "price_unverified"})

    def test_unverified_stock_is_not_orderable(self):
        with project.app.app_context():
            product = project.db.session.get(project.Product, self.product_id)
            product.stock_verified = False
            project.db.session.commit()
        token = self.csrf_token()
        response = self.test_client.post(
            "/api/orders",
            json={
                "name": "Unverified Stock Test",
                "phone": "9876543210",
                "address": "Test address",
                "items": [{"id": self.product_id, "quantity": 1}],
            },
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["code"], "insufficient_stock")

    def csrf_token(self):
        import re

        response = self.test_client.get("/")
        match = re.search(rb'<meta name="csrf-token" content="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()


if __name__ == "__main__":
    unittest.main()
