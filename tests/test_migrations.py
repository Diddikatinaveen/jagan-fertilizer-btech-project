import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import uuid

from tests.test_support import project


class DatabaseMigrationTests(unittest.TestCase):
    def test_legacy_products_and_orders_survive_additive_migration(self):
        database_name = f"phase9_migration_{uuid.uuid4().hex}.db"
        database_path = Path(project.app.instance_path) / database_name
        connection = sqlite3.connect(database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE product (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    category VARCHAR(40) NOT NULL,
                    description TEXT,
                    price FLOAT,
                    unit VARCHAR(40),
                    stock INTEGER,
                    image VARCHAR(250),
                    guidance_en TEXT,
                    guidance_te TEXT
                );
                CREATE TABLE "order" (
                    id INTEGER PRIMARY KEY,
                    customer_name VARCHAR(120) NOT NULL,
                    phone VARCHAR(30) NOT NULL,
                    address TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    total FLOAT NOT NULL,
                    status VARCHAR(30),
                    created_at DATETIME
                );
                """
            )
            connection.execute(
                "INSERT INTO product (id,name,category,description,price,unit,stock) "
                "VALUES (701,'Legacy Test Urea','Fertilizers','retained',0,'bag',7)"
            )
            connection.execute(
                'INSERT INTO "order" (id,customer_name,phone,address,items_json,total,status,created_at) '
                "VALUES (702,'Legacy Farmer','9876543210','Legacy address',?,10,'Received','2026-01-01 00:00:00')",
                (json.dumps([{
                    "id": 701,
                    "name": "Legacy Test Urea",
                    "quantity": 2,
                    "unit_price": 5,
                    "subtotal": 10,
                }]),),
            )
            connection.commit()
        finally:
            connection.close()

        environment = os.environ.copy()
        environment["DATABASE_URL"] = f"sqlite:///{database_name}"
        try:
            subprocess.run(
                [sys.executable, "-c", "import app"],
                cwd=Path(project.app.root_path),
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            migrated = sqlite3.connect(database_path)
            try:
                product = migrated.execute(
                    "SELECT name, stock, active FROM product WHERE id=701"
                ).fetchone()
                order = migrated.execute(
                    'SELECT customer_name, order_reference, user_id FROM "order" WHERE id=702'
                ).fetchone()
                item = migrated.execute(
                    "SELECT product_name, quantity, subtotal FROM order_item WHERE order_id=702"
                ).fetchone()
            finally:
                migrated.close()
            self.assertEqual(product, ("Legacy Test Urea", 7, 1))
            self.assertEqual(order[0], "Legacy Farmer")
            self.assertTrue(order[1].startswith("JF-"))
            self.assertIsNone(order[2])
            self.assertEqual(item, ("Legacy Test Urea", 2, 10.0))
        finally:
            database_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
