# JAGAN FERTILIZER — B.Tech Final-Year Project

A bilingual English/Telugu agricultural e-commerce project built with Flask
and SQLite. It brings a product catalogue, persistent browser cart, shop-
confirmed order requests, customer accounts, an administrator dashboard,
educational crop assistant, catalogue matching, and an optional leaf image
classifier into one responsive website. The project is for demonstration and
development; it is not configured for public production deployment.

The storefront opens with a short, tab-session cinematic brand introduction.
It can be skipped, follows the saved English/Telugu preference, and honors
reduced-motion settings. To preview it repeatedly during development, open
`http://127.0.0.1:5000/?replay-intro=1`; return to the plain homepage URL to
test the once-per-tab behavior.

The original uploaded organic-fertilizer logo was not available in the
workspace during this redesign. The intro temporarily uses the site's existing
inline JAGAN leaf brand mark in the center; no uploaded image was copied or
modified. When the original is provided, place it in `static/` and replace
the `.intro-logo` markup in `templates/index.html` with a Flask static URL.

## Project overview
Farmers often need a simple way to view available agricultural products and
learn general crop-care information. This project provides a small bilingual
catalogue and order-request workflow while keeping prices, inventory, customer
orders and administrative changes in the Flask backend.

### Problem statement
The project addresses fragmented access to local agricultural product
information and basic crop-care guidance. Its catalogue and assistant are
educational and demonstrative: they do not replace verified product labels,
soil testing or qualified agronomic advice.

### Objectives
- Present active products with search, category filters and details.
- Support English and Telugu across the storefront.
- Provide customer registration, authentication, order history and shop-
  confirmed order requests.
- Restrict inventory and order management to authorized administrators.
- Offer bounded crop-care FAQs and database-backed catalogue discovery.
- Provide a safe image-classification integration point without claiming
  disease detection until a compatible trained model has been evaluated.

### Technology stack
Python, Flask, Flask-SQLAlchemy, SQLAlchemy, SQLite, Jinja templates, HTML,
CSS, JavaScript, Pillow, NumPy, optional TensorFlow/Keras, and Waitress for a
local production-style WSGI run.

## 1. Requirements
- Python 3.10 or newer
- Internet browser
- Terminal / command prompt

## 2. Setup

### Windows
Open PowerShell in the extracted project folder and run:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe seed_products.py
.\.venv\Scripts\python.exe app.py
```
The checked-in `.env.example` contains placeholders only. Development can run
with its generated temporary session secret; use a stable, private
`SECRET_KEY` for longer-lived local sessions. `DATABASE_URL` can override the
default SQLite location. `python-dotenv` loads values from `.env`.

### macOS / Linux
```bash
cd JAGAN_FERTILIZER_BTech_Project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_products.py
python app.py
```

Open http://127.0.0.1:5000

The SQLite database is created automatically on first launch. Run the
idempotent catalogue seed script after installation to add the product
examples and local illustrations. Phase 5 and the catalogue additions use
additive migrations; back up `instance\jagan_fertilizer.db` before upgrading.
The original database was backed up before this phase to
`instance\jagan_fertilizer_phase5_backup_20261026.db`.
Phase 9 does not change the schema. Migration behavior is tested against a
throwaway legacy database rather than the shop database.

### Software and hardware requirements
- Python 3.10 or later for the base application; Windows PowerShell or another
  terminal and a modern browser.
- An internet connection is optional for the local storefront, but needed for
  a configured external AI provider and to install packages.
- No specific hardware benchmark has been established. TensorFlow training
  needs substantially more memory/storage and may benefit from a supported GPU;
  training time and performance have not been measured for this project.

## 3. Folder structure
```text
jagan_fertilizer_project/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── requirements-ml.txt
├── pytest.ini
├── .gitignore
├── .env.example
├── README.md
├── PROJECT_REPORT.md
├── seed_products.py
├── train_disease_model.py
├── templates/
│   ├── index.html
│   ├── auth.html
│   ├── account_orders.html
│   └── admin_dashboard.html
├── static/
│   ├── app.js
│   ├── auth.js
│   ├── admin.js
│   ├── translations.js
│   ├── style.css
│   ├── field-illustration.svg
│   ├── product-fertilizer.svg
│   ├── product-seeds.svg
│   └── images/
│       └── products/       # Local category illustrations; no shop photos supplied
└── tests/
    ├── __init__.py
    ├── test_catalogue_seed.py
    ├── test_core_workflows.py
    ├── test_crop_assistant.py
    ├── test_disease_recognition.py
    ├── test_migrations.py
    ├── test_recommendations.py
    └── test_support.py
```

The Phase 6 API tests are in `tests\test_crop_assistant.py`.

## 4. Homepage and product catalogue
The homepage requests product data from `GET /api/products` and supports search
and category filtering. Product names, bilingual descriptions, verified brand
names, pack size, availability, image paths and price flags are read from the
SQLite product records. Each catalogue entry has a local, category-specific SVG
illustration under `static/images/products/`. The illustrations are not genuine
product photographs or representations of a particular manufacturer's package;
replace them only with shop-supplied or otherwise authorized images.

Run `.\.venv\Scripts\python.exe seed_products.py` after installing dependencies
to add the catalogue examples. The script is idempotent and adds category
records without overwriting existing price or stock values. New unstocked
examples start with stock `0` and unconfirmed availability; update inventory
only with shop-confirmed stock and mark it verified in the admin panel.
Brand text is shown only when `brand_verified` is true. No manufacturer brands
or crop-protection products are currently verified, so those details/listings
remain hidden.

The following initial prices are **illustrative demo prices**, not current
market quotes or shop-confirmed offers:

| Catalogue item | Pack | Demo price |
|---|---:|---:|
| Urea | 45 kg | ₹300 |
| DAP | 50 kg | ₹1,350 |
| NPK 28-28-0 | 50 kg | ₹1,600 |
| Paddy Seeds | 5 kg | ₹500 |
| Micronutrient Fertilizer (Sample Pack) | Sample pack | ₹250 |

Demo prices are visible in the storefront with a clear label but remain
unverified. The browser may add them to the cart for demonstration, but the
checkout button and server-side order creation remain blocked until an
administrator confirms the actual price. Other seeded catalogue examples have
no price and no verified stock until the shop provides that information.
Pack-size or variety information not supplied by the shop is explicitly
marked as unprovided.

English is the default interface language. Use the English/తెలుగు selector in
the navigation to change languages. Translations are stored in
`static/translations.js`; the selected language persists in browser
`localStorage`. English and Telugu product descriptions are stored with each
product in SQLite.

### Cart and order requests
Add products to the cart, adjust or remove quantities, and submit customer name,
Indian mobile number, delivery address, and optional notes. Cart item IDs and
quantities persist in browser `localStorage`; prices, availability, totals and
stock deductions are recalculated and validated by the server. Products with
unverified demo or missing prices cannot be ordered. No payment is collected
online; the shop must confirm current prices and payment arrangements.

Orders and item snapshots are stored in SQLite. Additive migrations preserve
existing products and orders, add references, notes, optional customer
ownership, product visibility and verification flags, and retain legacy
anonymous orders without assigning them to a customer.

### Crop assistant
The homepage crop assistant supports English and Telugu. It uses a small,
bilingual FAQ fallback when `CROP_ASSISTANT_API_KEY` is not configured. The
fallback is limited to general education and does not diagnose plant disease
or provide application rates. Each answer identifies whether it came from the
FAQ fallback or an AI provider.

An optional OpenAI-compatible chat-completions provider can be configured in
the Flask server's environment. The API key is never embedded in website
assets or returned to the browser. Do not put credentials in source files or
commit them:
```powershell
$env:CROP_ASSISTANT_API_KEY = "your-provider-api-key"
$env:CROP_ASSISTANT_MODEL = "gpt-4o-mini"
# Optional; defaults to the OpenAI-compatible chat-completions endpoint.
$env:CROP_ASSISTANT_API_URL = "https://api.openai.com/v1/chat/completions"
.\.venv\Scripts\python.exe app.py
```
Use a provider-issued key and model name. The provider endpoint must use HTTPS;
HTTP is accepted only for localhost development endpoints. If the key is
absent, the app continues in fallback mode. The app does not claim that a real
model is available until a configured provider successfully answers a request.
Provider calls have a 12-second timeout; questions are limited to 1,000
characters and the endpoint allows 10 requests per IP address per five minutes
in the current app process. The in-memory rate limit resets when the process
restarts and is not shared across multiple workers. Configure a shared
rate-limiter before a multi-worker public deployment.

The assistant gives educational information, not a confirmed diagnosis or a
substitute for a qualified local agriculture officer. It must not invent
fertilizer dosages, pesticide instructions, product registrations or crop
outcomes. For crop-protection products, follow current approved labels,
protective-equipment directions and applicable local regulations. No chat
history is stored in the database or browser.

### Product recommendations
The recommendation form collects crop, growth stage, optional location and
soil-test notes, a farming question, and response language. Its default engine
uses transparent rule-based matching against available product names,
catalogue text and bilingual product guidance in SQLite. It is not a trained
AI model. It excludes inactive and out-of-stock products, does not recommend
crop-protection products, and only matches seeds during the sowing stage.
Catalogue records do not currently store verified crop-by-stage suitability,
so matches are discovery leads, not prescriptions. A vague symptom will not
be turned into a pesticide recommendation. A verified price is shown only
when the product's database `price_verified` flag is true; all product details
and IDs in results are fetched server-side.

If `CROP_ASSISTANT_API_KEY` is configured, the existing OpenAI-compatible
provider may rank only the database candidates already matched by the rules.
The response is restricted to their database IDs; the server still supplies
all display details and prices. AI ranking is not a claim of agronomic
suitability. Only the selected crop/stage and public matched-catalogue
information are sent for ranking; the farmer's free-text question, location
and soil notes are not sent to the provider. Provider errors return a safe
error instead of silently falling back. The endpoint limits requests to 8 per
IP per five minutes in each app process; this in-memory limit resets on
restart and is not shared across workers.

### Accounts and administrator access
Customers register at `/register` with a full name, email or Indian mobile
number, and a password of at least 12 characters. Passwords are stored as
Werkzeug scrypt hashes. Log in at `/login`; orders submitted while signed in
are linked to that account and shown at `/account/orders`. Existing anonymous
orders remain preserved but are not assigned to customer accounts.

Create the first administrator interactively from PowerShell. The command
prompts for the administrator name, email/mobile, and password; the password
is not accepted as a command-line argument or printed:
```powershell
.\.venv\Scripts\python.exe -m flask --app app create-admin
```
Administrator login is at `/admin/login`; the role-protected dashboard is at
`/admin`. Admins can add/edit products, set verified prices, adjust stock,
change visibility, verify registration details, view customer orders, and
update order status. Server-side role checks protect every admin page and API.

All state-changing requests, including checkout and admin APIs, require a
session-bound CSRF token. Website forms include it; same-origin scripts send
it as `X-CSRF-Token`. Login attempts are rate-limited using a hashed
identity/IP key. Session cookies are HttpOnly and SameSite=Lax. Local
development uses a randomly generated in-process secret and non-Secure cookies
for `http://127.0.0.1`; restarting invalidates existing sessions.

For production configuration (deployment is outside this phase), set a long
random secret outside source control and set `APP_ENV=production`. The app
refuses to start in production without `SECRET_KEY`, enables Secure session
cookies, and disables Flask debug mode. Secure cookies require HTTPS:
```powershell
$env:APP_ENV = "production"
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```
Keep the secret in a proper secret store, not in the project or source control.
Use HTTPS and a production WSGI server before exposing an instance publicly.

## 5. Database schema
`Product`: id, name, category, description, description_te, brand,
brand_verified, price, unit, stock, stock_verified, image, guidance_en,
guidance_te. `Product` also has `active`, `price_verified`, `is_demo_price`,
and `registration_verified` flags. Image paths refer to files served from
`static/images/products/`.
`User`: id, full_name, identity, identity_type, password_hash, role, is_active, created_at.
`Order`: id, user_id (nullable for legacy/anonymous orders), order_reference, customer_name, phone, address, notes, items_json, total, status, created_at.
`OrderItem`: id, order_id, product_id, product_name, quantity, unit_price, subtotal.
`LoginAttempt`: hashed identity/IP key, failure count, and short-window lock timestamps.

For a larger production system, add account recovery, email verification, audit logs and a properly provisioned WSGI deployment.

## 6. API endpoints
- `GET /api/products?category=Fertilizers&search=urea` — active catalogue products only
- `POST /api/chat` JSON: `{"message":"How should I understand a soil test?","lang":"en"}` — bilingual FAQ fallback or configured AI provider; `lang` may be `en`, `te`, or `auto`. Responses include `answer`, `language`, and `mode` (`fallback` or `ai`).
- `POST /api/recommend` — public, rate-limited catalogue matching. JSON example:
  `{"crop":"paddy","stage":"vegetative","location":"Guntur","soil":"Low nitrogen; pH 6.5","question":"Which fertilizer listings mention nitrogen?","lang":"en"}`
  Crop values: `paddy`, `wheat`, `maize`, `cotton`, `vegetables`, `other`
  (with `other_crop` required for `other`); stages: `sowing`, `vegetative`,
  `flowering`, `harvesting`; language: `en` or `te`.
- `GET /api/disease` — model status and installed supported crop/classes
- `POST /api/disease` multipart form fields `image`, `crop`, `lang` — preliminary image classification, only when a validated model is installed
- `POST /api/orders` — CSRF-protected order creation and stock transaction
- `GET /api/account/orders` and `GET /api/account/orders/<id>` — authenticated and restricted to the signed-in customer's orders
- `GET /api/admin/orders`, `GET /api/admin/products` — administrator-role protected
- `POST /api/admin/products`, `PATCH /api/admin/products/<id>` — administrator-role and CSRF protected
- `PATCH /api/admin/orders/<id>/status` — administrator-role and CSRF protected

## 7. Plant disease image classification
The web app uses a Keras MobileNetV2 transfer-learning classifier only when
both its model and matching metadata are present. This project currently
includes **no trained model, dataset, or disease class mapping**. Therefore,
the disease endpoint correctly reports `model_unavailable` until one is
trained and installed. No image is stored: uploads are validated and decoded
in memory, converted to RGB, resized to 224×224 with bilinear interpolation,
passed to the model as 0–255 RGB pixels, then scaled by the model's embedded
`Rescaling(1/127.5, offset=-1)` layer.

Do not use a dataset unless its source, exact license, permitted commercial
and research uses, attribution conditions, and crop/label limitations have
been checked. No dataset is downloaded or bundled by this project. Arrange
train, validation, and held-out test sets by plant/field or collection group
to avoid leakage; the trainer rejects exact duplicate image files across
splits but cannot detect near-duplicates or incorrect labels. Include healthy
and diseased classes and provide an explicit English/Telugu class mapping.
Example mapping file:
```json
{
  "paddy_healthy": {
    "crop": "paddy",
    "health": "healthy",
    "label_en": "Healthy leaf",
    "label_te": "ఆరోగ్యకరమైన ఆకు"
  },
  "paddy_example_disease": {
    "crop": "paddy",
    "health": "diseased",
    "label_en": "Example disease label",
    "label_te": "ఉదాహరణ వ్యాధి పేరు"
  }
}
```
Use a class name only when it is supported by the selected dataset's verified
labels. `crop` is the exact crop identifier expected from the form. The
classifier's confidence is not calibrated agronomic certainty; the default
inconclusive threshold is 0.65 and may be configured with
`DISEASE_CONFIDENCE_THRESHOLD` after validation.

Training is separate from the Flask app. Using a Python environment supported
by TensorFlow, install ML dependencies:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
```
Prepare a split dataset in this layout:
```text
dataset/
├── train/
│   ├── healthy/
│   ├── rice_blast/
│   └── bacterial_leaf_blight/
├── validation/
│   ├── healthy/
│   ├── rice_blast/
│   └── bacterial_leaf_blight/
└── test/
    ├── healthy/
    ├── rice_blast/
    └── bacterial_leaf_blight/
```
The folder names above are structural examples, not an assertion that those
classes are bundled or supported. Keep the same class directories in each
split. For example, with a properly licensed, locally prepared dataset and
matching `class-map.json`, run:
```powershell
.\.venv\Scripts\python.exe train_disease_model.py `
  --data .\dataset `
  --class-map .\class-map.json `
  --dataset-source "REPLACE_WITH_VERIFIED_DATASET_SOURCE" `
  --dataset-license "REPLACE_WITH_EXACT_LICENSE_AND_USE_TERMS" `
  --dataset-limitations "REPLACE_WITH_KNOWN_LABEL_AND_FIELD_LIMITATIONS" `
  --output .\models\plant_disease.keras `
  --epochs 8
```
The script requires at least two images per class in validation/test, verifies
class ordering and exact duplicate hashes across splits, trains MobileNetV2,
evaluates the held-out test set, and saves the `.keras` model with matching
`.metadata.json` containing class mappings, preprocessing contract, source,
license, limitations and evaluation results. Review held-out performance and
test on local field photos before enabling it. Test accuracy is not a guarantee
of field performance.

Run inference with the saved model path:
```powershell
$env:DISEASE_MODEL_PATH = ".\models\plant_disease.keras"
$env:DISEASE_CONFIDENCE_THRESHOLD = "0.65"
.\.venv\Scripts\python.exe app.py
```
The app loads the model once at startup with Keras safe mode and validates
metadata, class labels, input/output shape and softmax output. Supported
crops/classes appear in the UI and `GET /api/disease`. The upload endpoint
accepts JPG/JPEG/PNG only, limits uploads to 5 MB, validates image signatures,
dimensions and corruption, ignores the supplied filename for storage (no
persistent storage is used), and rejects unsupported crops. Low-confidence
results are inconclusive; top predictions are limited to that crop's trained
classes. The classifier only recognizes classes in its own mapping and does
not identify every plant disease.

Every prediction is preliminary screening, not a confirmed diagnosis. Do not
prescribe pesticide or fertilizer use from the result. Seek a qualified local
agriculture expert for uncertainty or severe crop damage.

## 8. Testing checklist
- Ask the crop assistant a general question in English and in Telugu; verify the reply language and visible mode label.
- With no `CROP_ASSISTANT_API_KEY`, verify responses identify the verified FAQ fallback.
- Test empty messages, non-JSON input, invalid language values and messages over 1,000 characters.
- Configure a provider only with server-side environment variables; test a successful response, provider error, 12-second timeout behavior and the per-process rate limit.
- Inspect browser-loaded HTML/JavaScript to confirm provider keys are not present; confirm the assistant does not persist chat history.
- Test paddy/vegetative recommendations with nitrogen soil-test context, sowing-stage paddy seed discovery, a different crop, an unknown crop, and no-match input.
- Verify inactive, out-of-stock, and crop-protection records are omitted; confirm price and details match the SQLite product row and that only verified prices are displayed.
- Run `.\.venv\Scripts\python.exe seed_products.py` twice against a disposable database; confirm no duplicates and that existing prices, stock, and orders remain unchanged.
- Load every visible product image, verify the category placeholder alt text, English/Telugu DB descriptions, demo price notices, search/category filters, product details and add-to-cart behavior. Confirm demo prices and unverified stock cannot be checked out.
- Check English/Telugu reasons and disclaimers, provider ranking allow-list enforcement, and Add to Cart/View Details actions on recommendation cards.
- Confirm disease screening reports unavailable when model files or TensorFlow are missing; test valid, corrupted, spoofed, oversized, too-small, unsupported-crop, and low-confidence images using a test-only fake model.
- Before enabling a real classifier, verify dataset license, class mapping, preprocessing, held-out test evaluation, supported crop list, and performance on local field images.
- Homepage loads and the catalogue displays database products.
- Search for `Urea`; filter by Fertilizers and Seeds.
- Confirm Crop protection explains that no verified listings are available.
- Switch between English and Telugu; open a product's details.
- Register with a valid email/mobile and a 12-character password; try duplicate registration.
- Confirm passwords are hashed in the `user` table; test login and logout.
- Verify unauthenticated customers cannot access account/admin pages or protected APIs.
- Log in as two customers and confirm each can see only their own orders, including when changing an order ID in the account API URL.
- Run `flask --app app create-admin`, then use the administrator to access `/admin`.
- As an administrator, add/edit a product, mark a price verified, change stock/visibility, and update an order status.
- Confirm admin APIs reject regular customers and mutation requests without a valid CSRF token.
- Add a product to the cart, change quantities, remove it, and refresh to check persistence.
- Confirm unpriced products cannot be submitted for checkout.
- With a verified non-zero product price, submit valid and invalid Indian mobile numbers.
- Check that insufficient stock, missing products, and zero/negative quantities are rejected.
- Verify the returned order reference and inspect the saved `Order` and `OrderItem` records.
- Confirm payment arrangements are described as shop-confirmed; no online payment is enabled.
- Check the layout at desktop and mobile widths.
- Confirm missing prices appear as placeholders and artwork is labelled illustrative.
- Restart the app and verify data persists in SQLite.

Install the test runner and run the complete suite from PowerShell:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -v
```
The unittest runner is also available without pytest:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests force an in-memory SQLite database before importing the application,
because importing `app.py` runs additive migrations. The migration test
creates and deletes its own throwaway SQLite database. Neither test path
connects to or modifies the shop database.

## 9. Development and production configuration
The `.env.example` contains placeholders only. Copy it to `.env` for local
configuration; `.env` is ignored by Git. Never commit real `SECRET_KEY`,
provider API keys, customer data, database backups, or trained model files.
The direct development runner uses `debug=False`. For a local WSGI smoke run
over HTTP, use Waitress in development mode:
```powershell
$env:APP_ENV = "development"
$env:DATABASE_URL = "sqlite:///jagan_fertilizer.db"
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 app:app
```
For production, set `APP_ENV=production` and a long random persistent
`SECRET_KEY` from a secret manager, then run Waitress behind a correctly
configured HTTPS reverse proxy. Production mode sets Secure session cookies,
so direct HTTP access cannot maintain browser sessions. Public hosting also
requires restricted network access, centralized secret management, backups
with a restore drill, monitoring, and legal/privacy review. Do not expose the
app publicly until the open deployment risks below are addressed. The built-in
in-memory API/login rate limits are per-process, not shared across instances;
replace them with a shared limiter before multi-worker or multi-instance
public service. SQLite is appropriate for this local project but should be
evaluated for concurrent production traffic.

Use the first-admin command only in a trusted terminal. Keep uploads,
database files, `.env`, logs, and model artifacts out of web-accessible paths.
Do not enable Flask debug mode in any deployment.

### Free Render deployment (demonstration only)
The root `render.yaml` defines a Free Python web service using Waitress. Render
Free web services have an ephemeral filesystem and spin down after inactivity;
do not use SQLite on the service for customer or shop records. This setup
connects to a separate PostgreSQL database using the `DATABASE_URL` secret.
The app normalizes standard `postgres://` and `postgresql://` provider URLs to
the installed psycopg 3 driver. A free-tier external database can have usage,
storage, inactivity, backup, and retention limits that may change; review the
provider's current terms. Neon currently offers a no-cost Free plan, but that
does not make this application production-ready.

To deploy:
1. Create a PostgreSQL project with a provider that has a free plan, and copy
   its pooled/SSL connection URL privately. Do not put that URL in Git or chat.
2. Push the source to GitHub and connect the repository in Render.
3. Create a new Blueprint instance and supply the database connection URL for
   `DATABASE_URL` when Render requests the unsynchronized secret. Do not apply
   the Blueprint if the service plan is not Free. The app expects the URL to
   connect to an empty/new database; it does not migrate or copy the local
   SQLite database, customer accounts, or orders.
4. Wait for deployment. Startup runs the idempotent catalogue seed script,
   creates the schema, and starts Waitress. Verify the service logs and the
   product API; confirm the connected database contains only the new hosted
   catalogue before creating real records.
5. Create the first administrator from the Render service's private Shell:
   `python -m flask --app app create-admin`. Enter the password only at the
   interactive prompt, then sign in at `/admin/login`.
6. Configure optional provider credentials only through Render's private
   environment-variable settings. No AI key or trained disease model is
   included in the repository or deployment configuration.

This is a **free-tier demonstration**, not a claim that the application is
ready for unrestricted public commerce. Free Render services can sleep and
have ephemeral local filesystems. PostgreSQL records persist only according
to the external provider's current free-plan terms; configure and test private
backups before entering real data. The app's rate limits are in-process, and
the catalogue contains illustrative prices and unverified stock. Keep real
customer transactions disabled until pricing, inventory, privacy, backups,
monitoring, and the remaining production risks have been reviewed.

For a consistent manual SQLite backup, stop the application first, then copy
the database to a dated backup path. Keep backups private and outside any
web-served directory:
```powershell
Copy-Item .\instance\jagan_fertilizer.db `
  ".\instance\jagan_fertilizer_backup_$(Get-Date -Format yyyyMMdd_HHmmss).db"
```
Verify the copy exists and periodically perform a restore test against a
separate database path; no production backup or restore drill was performed
for this phase.

## 10. Phase 9 verification record
The automated suite exercises storefront endpoints, bilingual resources,
registration/login/logout, password hashing, customer order isolation,
server-calculated checkout totals, stock rejection/rollback, admin operations,
CSRF and role checks, assistant fallback/provider errors, recommendation
matching, disease upload validation/fake-model predictions, and migration
preservation on a disposable database.

Executed on Windows with Python 3.13 on 2026-10-27:
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`: **34 tests
  passed** (exit code 0).
- `.\.venv\Scripts\python.exe -m py_compile ...`: **passed** for the Flask
  app, training utility and test modules.
- `train_disease_model.py --help`: **passed**; TensorFlow training was not run.
- Waitress smoke test on a throwaway SQLite database: homepage HTTP 200,
  catalogue returned four seeded products, chat returned FAQ fallback, and
  the disease status correctly reported no model.
- Browser check: English/Telugu switch and refresh persistence worked, mobile
  viewport had no horizontal overflow, cart quantity/state and product detail
  dialog worked, and the disease submit remained disabled without a model.
- The shop SQLite file SHA-256 fingerprint was unchanged across test runs.

The test run emitted non-fatal Python `ResourceWarning` messages during test
teardown/mock-provider handling; they did not cause test failures. Pytest was
not available in this environment, and fetching it for the optional dev
requirements failed because the package-index connection was reset. The same
suite was run successfully with Python's built-in unittest runner. External AI
provider behavior is tested with mocked responses only. No trained disease
model or dataset is installed; real-model loading and field-image accuracy
remain blocked.

The security review reported one critical debug-mode exposure: the direct
runner previously enabled Flask debug unless `APP_ENV=production` was set.
The direct runner now explicitly uses `debug=False`, with a regression test.
No other concrete findings above the review threshold were reported. The
review could not inspect any external host configuration.

## 11. Known limitations and remaining work
- The app is a project prototype, not a publicly deployed or load-tested
  commerce service. No deployment, HTTPS endpoint, production monitoring, or
  backup restore was performed in this workspace.
- The AI Crop Assistant defaults to its FAQ fallback. Provider calls are
  optional and require server-side credentials; mocked integration tests do
  not prove availability or correctness of an external provider.
- Product recommendations use transparent rule-based catalogue matching.
  An optional configured provider can rank already matched IDs only; neither
  mode establishes agronomic suitability.
- Disease recognition is unavailable until a dataset of verified source and
  license, class map, TensorFlow runtime, compatible trained model and
  evaluation results are supplied. No disease classes or accuracy results
  are currently available.
- The catalog's starter prices are unverified placeholders. Verify product
  details, prices, registration and stock before offering products for sale.
- Production operation still needs shared rate limiting, operational logging
  and alerting, account recovery/email verification, privacy and retention
  policies, tested backup/restore procedures, and jurisdiction-specific
  compliance review.

## 12. References and external data
No external crop-disease dataset is bundled, downloaded, or claimed as a
project source. Do not cite dataset accuracy until a dataset is selected,
licensed, trained, and evaluated with documented class coverage and split
methodology. Framework documentation:
- Flask: https://flask.palletsprojects.com/
- Flask-SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Pillow: https://pillow.readthedocs.io/
- NumPy: https://numpy.org/doc/
- TensorFlow/Keras (optional): https://www.tensorflow.org/ and
  https://keras.io/
- Waitress: https://docs.pylonsproject.org/projects/waitress/

## Safety and deployment notes
- Verify every product's actual label, composition, registration status, price, package size and stock before selling.
- Never invent pesticide dosage. Use only registered products and their current approved label directions.
- Get qualified local agricultural advice for field-specific treatment.
- Before real deployment, resolve the risks in section 9 and complete account recovery, email verification, audit logging, production HTTPS/WSGI configuration, privacy notice, tested backups, and applicable Indian e-commerce/agriculture compliance.
