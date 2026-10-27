import re
import unittest
import uuid
from unittest.mock import patch

from werkzeug.security import check_password_hash

from tests.test_support import project


class CoreWorkflowTests(unittest.TestCase):
    def test_database_url_normalizes_postgres_provider_schemes(self):
        self.assertEqual(
            project.normalize_database_url("postgres://user:pass@db.example.test/app"),
            "postgresql+psycopg://user:pass@db.example.test/app",
        )
        self.assertEqual(
            project.normalize_database_url("postgresql://user:pass@db.example.test/app"),
            "postgresql+psycopg://user:pass@db.example.test/app",
        )
        self.assertEqual(
            project.normalize_database_url("sqlite:///jagan_fertilizer.db"),
            "sqlite:///jagan_fertilizer.db",
        )

    def setUp(self):
        self.client = project.app.test_client()
        self.created_users = []
        self.created_orders = []
        with project.app.app_context():
            product = project.Product(
                name=f"Workflow Fertilizer {uuid.uuid4().hex[:8]}",
                category="Fertilizers",
                description="Verified test catalogue listing.",
                price=20.0,
                unit="test bag",
                stock=3,
                active=True,
                price_verified=True,
            )
            project.db.session.add(product)
            project.db.session.commit()
            self.product_id = product.id

    def tearDown(self):
        with project.app.app_context():
            for order_id in self.created_orders:
                order = project.db.session.get(project.Order, order_id)
                if order:
                    project.db.session.delete(order)
            for user_id in self.created_users:
                user = project.db.session.get(project.User, user_id)
                if user:
                    project.db.session.delete(user)
            product = project.db.session.get(project.Product, self.product_id)
            if product:
                project.db.session.delete(product)
            project.db.session.commit()

    @staticmethod
    def csrf(client, path="/"):
        response = client.get(path)
        match = re.search(rb'<meta name="csrf-token" content="([^"]+)"', response.data)
        if match:
            return match.group(1).decode()
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        if match:
            return match.group(1).decode()
        raise AssertionError(f"CSRF token not found on {path}")

    def create_user(self, role="customer", identity=None, password="secure-test-password"):
        identity = identity or f"{uuid.uuid4().hex}@example.test"
        with project.app.app_context():
            user = project.User(
                full_name="Workflow Test Farmer",
                identity=identity,
                identity_type="email",
                password_hash=project.generate_password_hash(password),
                role=role,
            )
            project.db.session.add(user)
            project.db.session.commit()
            user_id = user.id
        self.created_users.append(user_id)
        return user_id, identity, password

    def login(self, client, identity, password, endpoint="/login"):
        token = self.csrf(client, endpoint)
        response = client.post(
            endpoint,
            data={"identity": identity, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        return response

    def test_home_catalogue_search_categories_and_language_assets(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        for element_id in (
            b'id="introScreen"',
            b'id="introSkip"',
            b'id="introLanguageToggle"',
            b'id="siteContent"',
            b'id="shop"',
            b'id="detailsDialog"',
            b'id="cartDialog"',
            b'id="recommendations"',
            b'id="cropAssistant"',
            b'id="diseaseDetection"',
        ):
            self.assertIn(element_id, home.data)
        search = self.client.get("/api/products?search=urea")
        self.assertEqual(search.status_code, 200)
        self.assertTrue(any("Urea" in item["name"] for item in search.json))
        seeds = self.client.get("/api/products?category=Seeds")
        self.assertEqual(seeds.status_code, 200)
        self.assertTrue(all(item["category"] == "Seeds" for item in seeds.json))
        translation = self.client.get("/static/translations.js")
        self.assertEqual(translation.status_code, 200)
        self.assertIn("తెలుగు".encode(), translation.data)
        javascript = self.client.get("/static/app.js")
        self.assertEqual(javascript.status_code, 200)
        styles = self.client.get("/static/style.css")
        self.assertEqual(styles.status_code, 200)
        self.assertIn(b"sessionStorage.getItem(INTRO_SESSION_KEY)", javascript.data)
        self.assertIn(b"replay-intro", javascript.data)
        self.assertIn(b"prefers-reduced-motion", styles.data)
        self.assertIn(b"Growing a Greener Tomorrow", translation.data)
        self.assertIn("పచ్చని రేపటి కోసం పండిద్దాం".encode(), translation.data)
        translation.close()
        javascript.close()
        styles.close()

    def test_local_server_runner_keeps_debug_disabled(self):
        with patch.object(project.app, "run") as run:
            project.run_local_server()
        run.assert_called_once_with(debug=False)

    def test_registration_login_logout_and_hashed_password(self):
        identity = f"{uuid.uuid4().hex}@example.test"
        password = "a-long-test-password"
        token = self.csrf(self.client, "/register")
        registered = self.client.post(
            "/register",
            data={
                "full_name": "Test Customer",
                "identity": identity,
                "password": password,
                "csrf_token": token,
            },
        )
        self.assertEqual(registered.status_code, 302)
        with project.app.app_context():
            user = project.User.query.filter_by(identity=identity).one()
            user_id = user.id
            self.created_users.append(user_id)
            self.assertNotEqual(user.password_hash, password)
            self.assertTrue(check_password_hash(user.password_hash, password))

        duplicate = self.client.post(
            "/register",
            data={
                "full_name": "Test Customer",
                "identity": identity,
                "password": password,
                "csrf_token": token,
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        login = self.login(self.client, identity, password)
        self.assertEqual(login.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_id"], user_id)
            self.assertTrue(browser_session.permanent)
        self.assertEqual(self.client.get("/account/orders").status_code, 200)

        logout_token = self.csrf(self.client)
        logout = self.client.post("/logout", data={"csrf_token": logout_token})
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(self.client.get("/api/account/orders").status_code, 401)

    def test_order_history_is_owned_and_does_not_expose_customer_details(self):
        first_id, _, _ = self.create_user()
        second_id, _, _ = self.create_user()
        with project.app.app_context():
            order = project.Order(
                user_id=first_id,
                order_reference=f"JF-TEST-{uuid.uuid4().hex[:8]}",
                customer_name="Private Customer Name",
                phone="9876543210",
                address="Private delivery address",
                notes="Private note",
                items_json="[]",
                total=40.0,
            )
            order.items.append(project.OrderItem(
                product_id=self.product_id,
                product_name="Test item",
                quantity=2,
                unit_price=20.0,
                subtotal=40.0,
            ))
            project.db.session.add(order)
            project.db.session.commit()
            order_id = order.id
            self.created_orders.append(order_id)

        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = first_id
        own = self.client.get(f"/api/account/orders/{order_id}")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json["total"], 40.0)
        own_body = own.get_data(as_text=True)
        for private_value in ("Private Customer Name", "9876543210", "Private delivery address", "Private note"):
            self.assertNotIn(private_value, own_body)

        second_client = project.app.test_client()
        with second_client.session_transaction() as browser_session:
            browser_session["user_id"] = second_id
        denied = second_client.get(f"/api/account/orders/{order_id}")
        self.assertEqual(denied.status_code, 404)

    def test_checkout_uses_database_price_and_rolls_back_invalid_stock(self):
        token = self.csrf(self.client)
        payload = {
            "name": "Checkout Test Farmer",
            "phone": "+91 98765-43210",
            "address": "Test delivery address",
            "notes": "",
            "items": [{"id": self.product_id, "quantity": 2, "price": 0.01}],
            "total": 0.02,
        }
        placed = self.client.post(
            "/api/orders",
            json=payload,
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(placed.status_code, 201)
        self.assertEqual(placed.json["total"], 40.0)
        with project.app.app_context():
            order = project.db.session.get(project.Order, placed.json["order_id"])
            self.assertEqual(order.items[0].unit_price, 20.0)
            self.assertEqual(order.items[0].subtotal, 40.0)
            self.assertEqual(order.items[0].quantity, 2)
            self.assertEqual(project.db.session.get(project.Product, self.product_id).stock, 1)
            self.created_orders.append(order.id)

        too_many = self.client.post(
            "/api/orders",
            json={**payload, "items": [{"id": self.product_id, "quantity": 2}]},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(too_many.status_code, 409)
        self.assertEqual(too_many.json["code"], "insufficient_stock")
        missing = self.client.post(
            "/api/orders",
            json={**payload, "items": [{"id": 999999, "quantity": 1}]},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(missing.status_code, 409)
        invalid_quantity = self.client.post(
            "/api/orders",
            json={**payload, "items": [{"id": self.product_id, "quantity": 0}]},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(invalid_quantity.status_code, 400)
        with project.app.app_context():
            self.assertEqual(project.Order.query.count(), len(self.created_orders))
            self.assertEqual(project.db.session.get(project.Product, self.product_id).stock, 1)

    def test_admin_product_and_order_management_and_access_control(self):
        customer_id, customer_identity, customer_password = self.create_user()
        order_status = project.Order(
            order_reference=f"JF-TEST-{uuid.uuid4().hex[:8]}",
            customer_name="Admin Test Customer",
            phone="9876543210",
            address="Admin test address",
            items_json="[]",
            total=20.0,
        )
        admin_id, admin_identity, admin_password = self.create_user(
            role="admin",
            identity=f"{uuid.uuid4().hex}@admin.example.test",
        )
        with project.app.app_context():
            project.db.session.add(order_status)
            project.db.session.commit()
            order_id = order_status.id
            self.created_orders.append(order_id)

        customer_client = project.app.test_client()
        self.assertEqual(
            self.login(customer_client, customer_identity, customer_password).status_code,
            302,
        )
        customer_api = customer_client.get("/api/admin/products")
        self.assertEqual(customer_api.status_code, 403)
        self.assertEqual(customer_client.get("/admin").status_code, 403)

        self.assertEqual(self.login(self.client, admin_identity, admin_password, "/admin/login").status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)
        token = self.csrf(self.client)
        product_payload = {
            "name": f"Admin Created {uuid.uuid4().hex[:8]}",
            "category": "Fertilizers",
            "price": 25.0,
            "price_verified": True,
            "stock": 7,
            "active": True,
        }
        no_csrf = self.client.post("/api/admin/products", json=product_payload)
        self.assertEqual(no_csrf.status_code, 400)
        created = self.client.post(
            "/api/admin/products",
            json=product_payload,
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(created.status_code, 201)
        product_id = created.json["id"]
        with project.app.app_context():
            product = project.db.session.get(project.Product, product_id)
            self.assertIsNotNone(product)
            self.addCleanup(self._delete_product, product_id)

        updated = self.client.patch(
            f"/api/admin/products/{product_id}",
            json={"stock": 4},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["product"]["stock"], 4)
        changed_order = self.client.patch(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "Processing"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(changed_order.status_code, 200)
        self.assertEqual(changed_order.json["status"], "Processing")
        self.assertIn(order_id, [item["id"] for item in self.client.get("/api/admin/orders").json])

    @staticmethod
    def _delete_product(product_id):
        with project.app.app_context():
            product = project.db.session.get(project.Product, product_id)
            if product:
                project.db.session.delete(product)
                project.db.session.commit()


if __name__ == "__main__":
    unittest.main()
