"""Idempotently add catalogue examples without changing shop prices or stock."""

from pathlib import Path

from app import Product, app, db


CATALOGUE = (
    {
        "name": "Urea",
        "category": "Fertilizers",
        "description": "Urea fertilizer in a 45 kg demonstration pack. Check the actual bag for manufacturer, grade and label details.",
        "description_te": "45 కిలోల నమూనా ప్యాక్‌లో యూరియా ఎరువు. తయారీదారు, గ్రేడ్ మరియు లేబుల్ వివరాలను అసలు సంచిపై పరిశీలించండి.",
        "unit": "45 kg bag",
        "demo_price": 300,
        "image": "images/products/urea-placeholder.svg",
        "guidance_en": "Demonstration catalogue listing only. Verify the product identity and label. Use soil-test-based local guidance; this listing does not provide an application rate.",
        "guidance_te": "ఇది నమూనా కాటలాగ్ జాబితా మాత్రమే. ఉత్పత్తి వివరాలు, లేబుల్‌ను నిర్ధారించండి. నేల పరీక్ష ఆధారిత స్థానిక సలహా తీసుకోండి; ఈ జాబితా వినియోగ మోతాదును సూచించదు.",
    },
    {
        "name": "DAP",
        "category": "Fertilizers",
        "description": "DAP fertilizer in a 50 kg demonstration pack. Verify the actual product and guaranteed analysis on its label.",
        "description_te": "50 కిలోల నమూనా ప్యాక్‌లో డీఏపీ ఎరువు. అసలు ఉత్పత్తి, హామీ పోషక వివరాలను లేబుల్‌పై నిర్ధారించండి.",
        "unit": "50 kg bag",
        "demo_price": 1350,
        "image": "images/products/dap-placeholder.svg",
        "guidance_en": "Demonstration catalogue listing only. Verify the product identity and label. Use soil-test-based local guidance; this listing does not provide an application rate.",
        "guidance_te": "ఇది నమూనా కాటలాగ్ జాబితా మాత్రమే. ఉత్పత్తి వివరాలు, లేబుల్‌ను నిర్ధారించండి. నేల పరీక్ష ఆధారిత స్థానిక సలహా తీసుకోండి; ఈ జాబితా వినియోగ మోతాదును సూచించదు.",
    },
    {
        "name": "NPK 28-28-0",
        "category": "Fertilizers",
        "description": "NPK 28-28-0 fertilizer in a 50 kg demonstration pack. Confirm the grade on the actual product label.",
        "description_te": "50 కిలోల నమూనా ప్యాక్‌లో NPK 28-28-0 ఎరువు. అసలు ఉత్పత్తి లేబుల్‌పై గ్రేడ్‌ను నిర్ధారించండి.",
        "unit": "50 kg bag",
        "demo_price": 1600,
        "image": "images/products/npk-28-28-0-placeholder.svg",
        "guidance_en": "Demonstration catalogue listing only. Verify the product identity and label. Use soil-test-based local guidance; this listing does not provide an application rate.",
        "guidance_te": "ఇది నమూనా కాటలాగ్ జాబితా మాత్రమే. ఉత్పత్తి వివరాలు, లేబుల్‌ను నిర్ధారించండి. నేల పరీక్ష ఆధారిత స్థానిక సలహా తీసుకోండి; ఈ జాబితా వినియోగ మోతాదును సూచించదు.",
    },
    {
        "name": "Other NPK Fertilizer Grades",
        "category": "Fertilizers",
        "description": "Category placeholder for other NPK grades. No specific grade, manufacturer or pack size has been confirmed.",
        "description_te": "ఇతర NPK గ్రేడ్‌లకు వర్గ నమూనా మాత్రమే. నిర్దిష్ట గ్రేడ్, తయారీదారు లేదా ప్యాక్ పరిమాణం నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/npk-grades-placeholder.svg",
        "guidance_en": "No product-specific analysis or approved use information has been supplied. Review the actual package label and obtain local advice before use.",
        "guidance_te": "ఉత్పత్తి-నిర్దిష్ట పోషక విశ్లేషణ లేదా ఆమోదిత వినియోగ సమాచారం అందించబడలేదు. వాడకానికి ముందు అసలు ప్యాకేజీ లేబుల్‌ను పరిశీలించి స్థానిక సలహా పొందండి.",
    },
    {
        "name": "Organic Manure and Compost",
        "category": "Fertilizers",
        "description": "Category placeholder for organic manure or compost. Source, composition, certification and pack size are not confirmed.",
        "description_te": "సేంద్రియ ఎరువు లేదా కంపోస్ట్‌కు వర్గ నమూనా మాత్రమే. మూలం, కూర్పు, ధృవీకరణ మరియు ప్యాక్ పరిమాణం నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/organic-compost-placeholder.svg",
        "guidance_en": "This is not a verified product specification. Confirm source, composition and applicable label information with the shop.",
        "guidance_te": "ఇది ధృవీకరించిన ఉత్పత్తి వివరాలు కాదు. మూలం, కూర్పు మరియు వర్తించే లేబుల్ సమాచారాన్ని షాపుతో నిర్ధారించండి.",
    },
    {
        "name": "Micronutrient Fertilizer (Sample Pack)",
        "category": "Fertilizers",
        "description": "Micronutrient fertilizer sample-pack placeholder. Nutrient composition and product-specific details are not confirmed.",
        "description_te": "సూక్ష్మపోషక ఎరువు నమూనా ప్యాక్ ఉదాహరణ. పోషక కూర్పు, ఉత్పత్తి-నిర్దిష్ట వివరాలు నిర్ధారించబడలేదు.",
        "unit": "Sample pack",
        "demo_price": 250,
        "image": "images/products/micronutrient-placeholder.svg",
        "guidance_en": "The displayed price is illustrative only. Confirm the nutrient composition and label; consult a soil test or qualified local expert.",
        "guidance_te": "చూపించిన ధర ఉదాహరణ మాత్రమే. పోషక కూర్పు, లేబుల్‌ను నిర్ధారించండి; నేల పరీక్ష లేదా అర్హత కలిగిన స్థానిక నిపుణుడిని సంప్రదించండి.",
    },
    {
        "name": "Paddy Seeds",
        "category": "Seeds",
        "description": "Paddy seeds in a 5 kg demonstration pack. Variety, lot, germination and treatment details have not been verified.",
        "description_te": "5 కిలోల నమూనా ప్యాక్‌లో వరి విత్తనాలు. రకం, లాట్, మొలక శాతం మరియు శుద్ధి వివరాలు ధృవీకరించబడలేదు.",
        "unit": "5 kg pack",
        "demo_price": 500,
        "image": "images/products/paddy-seeds-placeholder.svg",
        "guidance_en": "Demonstration listing only. Check variety, certification, lot number, germination, validity and supplier instructions on the actual pack.",
        "guidance_te": "ఇది నమూనా జాబితా మాత్రమే. అసలు ప్యాక్‌పై రకం, ధృవీకరణ, లాట్ నంబర్, మొలక శాతం, గడువు మరియు సరఫరాదారు సూచనలు చూడండి.",
    },
    {
        "name": "Wheat Seeds",
        "category": "Seeds",
        "description": "Wheat seed category placeholder. Variety, pack size, lot, germination and treatment details are not confirmed.",
        "description_te": "గోధుమ విత్తనాల వర్గ నమూనా. రకం, ప్యాక్ పరిమాణం, లాట్, మొలక శాతం మరియు శుద్ధి వివరాలు నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/wheat-seeds-placeholder.svg",
        "guidance_en": "Confirm the variety, region and season suitability, certification, lot number and package instructions with the supplier.",
        "guidance_te": "రకం, ప్రాంతం మరియు సీజన్‌కు అనుకూలత, ధృవీకరణ, లాట్ నంబర్ మరియు ప్యాకేజీ సూచనలను సరఫరాదారుతో నిర్ధారించండి.",
    },
    {
        "name": "Vegetable Seeds",
        "category": "Seeds",
        "description": "Vegetable seed category placeholder. Crop variety, pack size, lot and germination details are not confirmed.",
        "description_te": "కూరగాయల విత్తనాల వర్గ నమూనా. పంట రకం, ప్యాక్ పరిమాణం, లాట్ మరియు మొలక శాతం వివరాలు నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/vegetable-seeds-placeholder.svg",
        "guidance_en": "Confirm the variety, region and season suitability, certification, lot number and package instructions with the supplier.",
        "guidance_te": "రకం, ప్రాంతం మరియు సీజన్‌కు అనుకూలత, ధృవీకరణ, లాట్ నంబర్ మరియు ప్యాకేజీ సూచనలను సరఫరాదారుతో నిర్ధారించండి.",
    },
    {
        "name": "Biofertilizer",
        "category": "Fertilizers",
        "description": "Biofertilizer category placeholder. Organism, formulation, registration, storage and pack details are not confirmed.",
        "description_te": "జీవ ఎరువుల వర్గ నమూనా. సూక్ష్మజీవి, ఫార్ములేషన్, నమోదు, నిల్వ మరియు ప్యాక్ వివరాలు నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/biofertilizer-placeholder.svg",
        "guidance_en": "Confirm the organism, formulation, registration and storage/expiry directions from the actual product label before use.",
        "guidance_te": "వాడకానికి ముందు అసలు ఉత్పత్తి లేబుల్‌లోని సూక్ష్మజీవి, ఫార్ములేషన్, నమోదు, నిల్వ మరియు గడువు సూచనలను నిర్ధారించండి.",
    },
    {
        "name": "Soil Improvement Product",
        "category": "Fertilizers",
        "description": "Soil-improvement product category placeholder. Product type, composition and approved claims have not been confirmed.",
        "description_te": "నేల మెరుగుదల ఉత్పత్తి వర్గ నమూనా. ఉత్పత్తి రకం, కూర్పు మరియు ఆమోదిత వివరాలు నిర్ధారించబడలేదు.",
        "unit": "Pack size not provided",
        "demo_price": None,
        "image": "images/products/soil-improvement-placeholder.svg",
        "guidance_en": "No product-specific specification is available. Identify the soil issue with a soil test and check the actual package label.",
        "guidance_te": "ఉత్పత్తి-నిర్దిష్ట వివరాలు అందుబాటులో లేవు. నేల సమస్యను పరీక్ష ద్వారా గుర్తించి అసలు ప్యాకేజీ లేబుల్‌ను పరిశీలించండి.",
    },
)

LEGACY_DESCRIPTIONS = {
    "Nitrogen fertilizer. Confirm grade and bag details on the label.",
    "Diammonium phosphate fertilizer; check the guaranteed analysis on the bag.",
    "Nutrient grade shown as N-P₂O₅-K₂O; verify the product label.",
    "Enter the actual variety, lot number and package details before selling.",
}


def existing_image_is_valid(relative_path):
    static_root = Path(app.static_folder).resolve()
    normalized_path = str(relative_path or "").replace("\\", "/").lstrip("/")
    if normalized_path.lower().startswith("static/"):
        normalized_path = normalized_path[7:]
    if not normalized_path or ".." in Path(normalized_path).parts:
        return False
    candidate = (static_root / normalized_path).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return False
    return candidate.is_file()


def seed_catalogue():
    inserted = 0
    updated = 0
    with app.app_context():
        try:
            for item in CATALOGUE:
                product = Product.query.filter(
                    db.func.lower(Product.name) == item["name"].casefold(),
                    Product.category == item["category"],
                ).first()
                if product is None:
                    product = Product(
                        name=item["name"],
                        category=item["category"],
                        description=item["description"],
                        description_te=item["description_te"],
                        brand="",
                        brand_verified=False,
                        price=float(item["demo_price"] or 0),
                        unit=item["unit"],
                        stock=0,
                        stock_verified=False,
                        image=item["image"],
                        guidance_en=item["guidance_en"],
                        guidance_te=item["guidance_te"],
                        active=True,
                        price_verified=False,
                        is_demo_price=item["demo_price"] is not None,
                        registration_verified=False,
                    )
                    db.session.add(product)
                    inserted += 1
                    continue

                if not product.description or product.description in LEGACY_DESCRIPTIONS:
                    product.description = item["description"]
                if not product.description_te:
                    product.description_te = item["description_te"]
                if not product.brand:
                    product.brand = ""
                if (
                    item["name"] == "Paddy Seeds"
                    and product.unit == "pack"
                ):
                    product.unit = item["unit"]
                if not product.guidance_en:
                    product.guidance_en = item["guidance_en"]
                if not product.guidance_te:
                    product.guidance_te = item["guidance_te"]
                if not existing_image_is_valid(product.image or ""):
                    product.image = item["image"]

                if product.price_verified:
                    product.is_demo_price = False
                elif not product.price and item["demo_price"] is not None:
                    product.price = float(item["demo_price"])
                    product.is_demo_price = True
                elif product.is_demo_price and item["demo_price"] is not None:
                    product.is_demo_price = float(product.price) == float(item["demo_price"])

                updated += 1

            legacy_protection = Product.query.filter_by(
                name="Crop Protection Product",
                category="Pesticides",
            ).first()
            if legacy_protection and not existing_image_is_valid(legacy_protection.image or ""):
                legacy_protection.image = "images/products/crop-protection-placeholder.svg"
                updated += 1

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return inserted, updated


if __name__ == "__main__":
    inserted, updated = seed_catalogue()
    print(f"Catalogue seed complete: {inserted} inserted, {updated} existing records checked.")
