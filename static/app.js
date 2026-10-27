const translations = window.JAGAN_TRANSLATIONS;
let lang = readSavedLanguage();
let category = "All";
let products = [];
let cart = readSavedCart();
let searchTimer;
let requestController;
let dialogProductId = null;
let lastOrderReference = null;
let cartMessageState = null;
let assistantRequestController = null;
let recommendationRequestController = null;
let recommendationData = null;
let diseaseModelInfo = null;
let diseasePreviewUrl = null;
let diseaseRequestController = null;
let introTimer = null;
const $ = id => document.getElementById(id);
const text = key => translations[lang].ui[key] || translations.en.ui[key] || key;
const INTRO_SESSION_KEY = "jagan-fertilizer-intro-seen";

function readSavedLanguage() {
  try {
    return localStorage.getItem("jagan-fertilizer-language") === "te" ? "te" : "en";
  } catch (error) {
    console.warn("Could not read the saved language preference:", error);
    return "en";
  }
}

function saveLanguage(language) {
  try {
    localStorage.setItem("jagan-fertilizer-language", language);
  } catch (error) {
    console.warn("Could not save the language preference:", error);
  }
}

function readSavedCart() {
  try {
    const saved = JSON.parse(localStorage.getItem("jagan-fertilizer-cart") || "[]");
    if (!Array.isArray(saved)) return [];
    return saved.filter(item =>
      item && Number.isSafeInteger(item.id) && item.id > 0 &&
      Number.isSafeInteger(item.quantity) && item.quantity > 0
    ).map(item => ({id: item.id, quantity: item.quantity}));
  } catch (error) {
    console.warn("Could not read the saved cart:", error);
    return [];
  }
}

function saveCart() {
  try {
    localStorage.setItem("jagan-fertilizer-cart", JSON.stringify(cart));
  } catch (error) {
    console.warn("Could not save the cart:", error);
    showCartTranslation("cartSaveFailed", true);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function getProductDescription(product) {
  return (lang === "te" ? product.description_te : product.description) || product.description || "";
}

function getCategoryName(productCategory) {
  return translations[lang].categories[productCategory] || productCategory || "";
}

function getUnitName(unit) {
  if (lang === "te") {
    return unit
      .replace(/Pack size not provided/gi, text("packSizeNotProvided"))
      .replace(/Sample pack/gi, text("samplePack"))
      .replace(/\bpack\b/gi, "ప్యాక్")
      .replace(/\bbag\b/gi, "సంచి");
  }
  return unit;
}

function formatPrice(price) {
  return `₹${Number(price).toLocaleString(lang === "te" ? "te-IN" : "en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })}`;
}

function formatMoneyOrPending(amount) {
  return Number(amount) > 0 ? formatPrice(amount) : text("priceConfirm");
}

function fillMessage(key, values = {}) {
  return text(key).replace(/\{(\w+)\}/g, (match, name) =>
    Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match
  );
}

function categoryPlaceholder(category) {
  return category === "Seeds"
    ? "/static/images/products/paddy-seeds-placeholder.svg"
    : category === "Pesticides"
      ? "/static/images/products/crop-protection-placeholder.svg"
      : "/static/images/products/npk-grades-placeholder.svg";
}

function normalizedProductImagePath(product) {
  let image = String(product.image || "").replace(/\\/g, "/").replace(/^\/+/, "");
  if (image.toLowerCase().startsWith("static/")) image = image.slice(7);
  if (
    !/^[a-z0-9._/-]+\.(?:svg|png|jpe?g|webp|gif)$/i.test(image) ||
    image.split("/").includes("..")
  ) return "";
  return image;
}

function productImage(product) {
  const image = normalizedProductImagePath(product);
  return image
    ? `/static/${image.split("/").map(encodeURIComponent).join("/")}`
    : categoryPlaceholder(product.category);
}

function productImageAlt(product) {
  const image = normalizedProductImagePath(product);
  return image && !/-placeholder\.svg$/i.test(image)
    ? fillMessage("productImageAlt", {name: product.name})
    : fillMessage("illustrativeProductImage", {name: product.name});
}

function productImageFallbackAttribute(product) {
  return `data-fallback-image="${categoryPlaceholder(product.category)}"`;
}

function getProduct(id) {
  return products.find(product => Number(product.id) === id);
}

function displayableProducts(rows) {
  return rows.filter(product =>
    product.category !== "Pesticides" || product.registration_verified === true
  );
}

function filteredTeluguProducts(rows) {
  const query = $("search").value.trim().toLocaleLowerCase();
  if (lang !== "te" || !query) return rows;
  return rows.filter(product => {
    const translatedDescription = getProductDescription(product);
    return [
      product.name,
      product.description,
      product.category,
      getCategoryName(product.category),
      translatedDescription
    ].some(value => String(value || "").toLocaleLowerCase().includes(query));
  });
}

function renderProducts(rows) {
  const grid = $("productGrid");
  const visibleProducts = displayableProducts(filteredTeluguProducts(rows));
  grid.setAttribute("aria-busy", "false");

  if (!visibleProducts.length) {
    const protectionMessage = category === "Pesticides";
    grid.innerHTML = `<div class="empty-state"><span aria-hidden="true">✳</span><h3>${protectionMessage ? text("noProtection") : text("noProducts")}</h3><p>${protectionMessage ? text("noProtectionHint") : text("noProductsHint")}</p></div>`;
    $("resultCount").textContent = formatItemCount(0);
    renderCart();
    return;
  }

  $("resultCount").textContent = formatItemCount(visibleProducts.length);
  const cards = visibleProducts.map(product => {
    const stockVerified = product.stock_verified === true;
    const inStock = stockVerified && Number(product.stock) > 0;
    const stockText = !stockVerified
      ? text("availabilityUnconfirmed")
      : inStock
      ? `${text("inStock")} · ${Number(product.stock).toLocaleString(lang === "te" ? "te-IN" : "en-IN")}`
      : text("outOfStock");
    const image = productImage(product);
    const description = getProductDescription(product);
    const brand = product.brand_verified === true ? String(product.brand || "").trim() : "";
    return `<article class="product-card">
      <div class="product-image-wrap">
        <img class="product-image" src="${image}" ${productImageFallbackAttribute(product)} alt="${escapeHtml(productImageAlt(product))}" loading="lazy">
        <span class="product-label">${text("illustrativeImage")}</span>
      </div>
      <div class="product-info">
        <span class="product-category" aria-label="${text("productCategory")}">${escapeHtml(getCategoryName(product.category))}</span>
        <h3>${escapeHtml(product.name)}</h3>
        ${brand ? `<p class="product-brand">${text("brandLabel")}: ${escapeHtml(brand)}</p>` : ""}
        <p class="product-description">${escapeHtml(description)}</p>
        <div class="product-meta">
          ${renderProductPrice(product)}
          <span class="stock-status${!stockVerified ? " pending-status" : inStock ? "" : " out-of-stock"}">${stockText}</span>
        </div>
        <div class="product-actions">
          <span class="product-unit">${product.unit ? `${text("packSizeLabel")}: ${escapeHtml(getUnitName(product.unit))}` : ""}</span>
          <div class="product-card-actions">
            <button class="details-button" type="button" data-product-id="${Number(product.id)}">${text("viewDetails")}</button>
            <button class="add-cart-button" type="button" data-add-product="${Number(product.id)}" ${!inStock ? "disabled" : ""}>${text("addToCart")}</button>
          </div>
        </div>
      </div>
    </article>`;
  }).join("");

  const knownFertilizers = ["Urea", "DAP", "NPK 28-28-0"];
  const showFertilizerPlaceholder = category === "Fertilizers" &&
    !$("search").value.trim() &&
    !visibleProducts.some(product => !knownFertilizers.includes(product.name));
  const fertilizerPlaceholder = showFertilizerPlaceholder
    ? `<article class="product-card placeholder-card">
        <div class="product-image-wrap">
          <img class="product-image" src="/static/product-fertilizer.svg" alt="${text("illustrativeImage")}: ${text("otherFertilizers")}" loading="lazy">
          <span class="product-label">${text("listingPending")}</span>
        </div>
        <div class="product-info">
          <span class="product-category">${escapeHtml(getCategoryName("Fertilizers"))}</span>
          <h3>${text("otherFertilizers")}</h3>
          <p class="product-description">${text("fertilizerPlaceholder")}</p>
          <div class="product-meta">
            <span class="product-price placeholder">${text("priceNotProvided")}</span>
            <span class="stock-status pending-status">${text("listingPending")}</span>
          </div>
          <div class="product-actions">
            <span class="product-unit">${text("detailsPending")}</span>
            <button class="details-button" type="button" disabled>${text("detailsPending")}</button>
          </div>
        </div>
      </article>`
    : "";
  grid.innerHTML = cards + fertilizerPlaceholder;
  renderCart();
}

function setCartMessage(message, isError = false) {
  cartMessageState = null;
  const output = $("cartMessage");
  output.textContent = message;
  output.classList.toggle("error", isError);
}

function setCartTranslation(key, isError = false, values = {}) {
  const message = fillMessage(key, values);
  setCartMessage(message, isError);
  cartMessageState = {key, isError, values};
}

function showCartTranslation(key, isError = false, values = {}) {
  setCartTranslation(key, isError, values);
  if (!$("cartDialog").open) $("cartDialog").showModal();
}

function addToCart(id) {
  const product = getProduct(id);
  if (!product) {
    showCartTranslation("productUnavailable", true);
    return;
  }
  if (product.stock_verified !== true) {
    showCartTranslation("availabilityUnconfirmed", true);
    return;
  }
  if (Number(product.stock) < 1) {
    showCartTranslation("stockUnavailable", true);
    return;
  }
  const item = cart.find(entry => entry.id === id);
  if (item) {
    if (item.quantity >= Number(product.stock)) {
      showCartTranslation("quantityExceedsAvailable", true, {
        stock: Number(product.stock),
        name: product.name
      });
      return;
    }
    item.quantity += 1;
  } else {
    cart.push({id, quantity: 1});
  }
  saveCart();
  renderCart();
  setCartTranslation("addedToCart");
}

function changeCartQuantity(id, delta) {
  const item = cart.find(entry => entry.id === id);
  if (!item) return;
  if (delta < 0 && item.quantity <= 1) {
    removeCartItem(id);
    return;
  }
  if (delta > 0) {
    const product = getProduct(id);
    if (!product) {
      showCartTranslation("productUnavailable", true);
      return;
    }
    if (product.stock_verified !== true) {
      showCartTranslation("availabilityUnconfirmed", true);
      return;
    }
    if (item.quantity >= Number(product.stock)) {
      showCartTranslation("quantityExceedsAvailable", true, {
        stock: Number(product.stock),
        name: product.name
      });
      return;
    }
  }
  item.quantity += delta;
  saveCart();
  renderCart();
  setCartMessage("");
}

function removeCartItem(id) {
  cart = cart.filter(item => item.id !== id);
  saveCart();
  renderCart();
  setCartTranslation("removedFromCart");
}

function renderCart() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  $("cartCount").textContent = count.toLocaleString(lang === "te" ? "te-IN" : "en-IN");
  $("cartOpen").setAttribute("aria-label", fillMessage("cartCount", {count}));
  if (!cart.length) {
    $("cartItems").innerHTML = `<div class="cart-empty"><p>${text("cartEmpty")}</p><small>${text("cartEmptyHint")}</small></div>`;
    $("checkoutSummary").innerHTML = `<p class="summary-empty">${text("cartEmpty")}</p>`;
    $("cartTotal").textContent = text("priceConfirm");
    $("checkoutTotal").textContent = text("priceConfirm");
    $("checkoutSubmit").disabled = true;
    return;
  }

  let total = 0;
  let hasUnpricedItems = false;
  let hasInvalidPrice = false;
  let available = true;
  $("cartItems").innerHTML = cart.map(item => {
    const product = getProduct(item.id);
    if (!product) {
      available = false;
      return `<article class="cart-item unavailable-item">
        <div class="cart-item-info"><strong>${text("productUnavailable")}</strong><small>#${item.id}</small></div>
        <button class="remove-item" type="button" data-remove-item="${item.id}" aria-label="${text("removeItem")}">×</button>
      </article>`;
    }
    const price = Number(product.price);
    const hasDisplayPrice = Number.isFinite(price) && price > 0 &&
      (product.price_verified === true || product.is_demo_price === true);
    const hasVerifiedPrice = product.price_verified === true && hasDisplayPrice;
    const displayedSubtotal = hasDisplayPrice ? price * item.quantity : null;
    if (!hasVerifiedPrice) {
      hasInvalidPrice = true;
      if (!hasDisplayPrice) hasUnpricedItems = true;
    }
    if (hasDisplayPrice) {
      total += displayedSubtotal;
    }
    const stock = Number(product.stock) || 0;
    const stockVerified = product.stock_verified === true;
    const stockExceeded = stockVerified && item.quantity > stock;
    if (!stockVerified || stockExceeded) available = false;
    const stockWarning = !stockVerified
      ? text("availabilityUnconfirmed")
      : stockExceeded
        ? fillMessage("quantityExceedsAvailable", {stock, name: product.name})
        : "";
    const unitPriceText = hasDisplayPrice
      ? `${formatPrice(price)}${product.is_demo_price ? ` · ${text("demoPriceLabel")}` : ""}`
      : text("priceConfirm");
    const subtotalText = displayedSubtotal === null
      ? text("priceConfirm")
      : `${formatPrice(displayedSubtotal)}${product.is_demo_price ? ` · ${text("demoPriceLabel")}` : ""}`;
    return `<article class="cart-item${stockExceeded ? " unavailable-item" : ""}">
      <img src="${productImage(product)}" ${productImageFallbackAttribute(product)} alt="" class="cart-item-image">
      <div class="cart-item-info">
        <strong>${escapeHtml(product.name)}</strong>
        <small>${text("unitPrice")}: ${unitPriceText}</small>
        <small>${text("subtotal")}: <b>${subtotalText}</b></small>
        ${stockWarning ? `<small class="stock-warning">${stockWarning}</small>` : ""}
      </div>
      <div class="cart-item-controls">
        <div class="quantity-control">
          <button type="button" data-quantity-change="-1" data-item-id="${item.id}" aria-label="${text("decreaseQuantity")}">−</button>
          <span aria-live="polite">${item.quantity.toLocaleString(lang === "te" ? "te-IN" : "en-IN")}</span>
          <button type="button" data-quantity-change="1" data-item-id="${item.id}" aria-label="${text("increaseQuantity")}" ${!stockVerified || item.quantity >= stock ? "disabled" : ""}>+</button>
        </div>
        <button class="remove-item" type="button" data-remove-item="${item.id}" aria-label="${text("removeItem")}">×</button>
      </div>
    </article>`;
  }).join("");

  const summaryRows = cart.map(item => {
    const product = getProduct(item.id);
    if (!product) {
      return `<div class="summary-row"><span>${text("productUnavailable")}</span><strong>${text("priceConfirm")}</strong></div>`;
    }
    const unitPrice = Number(product.price);
    const hasDisplayPrice = Number.isFinite(unitPrice) && unitPrice > 0 &&
      (product.price_verified === true || product.is_demo_price === true);
    const subtotal = hasDisplayPrice
      ? `${formatPrice(unitPrice * item.quantity)}${product.is_demo_price ? ` · ${text("demoPriceLabel")}` : ""}`
      : text("priceConfirm");
    return `<div class="summary-row"><span>${escapeHtml(product.name)} × ${item.quantity}</span><strong>${subtotal}</strong></div>`;
  }).join("");
  $("checkoutSummary").innerHTML = summaryRows;
  const totalText = hasUnpricedItems ? text("priceConfirm") : formatPrice(total);
  $("cartTotal").textContent = totalText;
  $("checkoutTotal").textContent = totalText;
  $("checkoutSubmit").disabled = !available || hasInvalidPrice;
  if (hasInvalidPrice) setCartTranslation("priceMustBeConfirmed", true);
  if (!available) setCartTranslation("cartNeedsAttention", true);
}

function formatItemCount(count) {
  const number = Number(count).toLocaleString(lang === "te" ? "te-IN" : "en-IN");
  return `${number} ${count === 1 ? text("itemSingular") : text("itemPlural")}`;
}

function renderProductPrice(product) {
  const amount = Number(product.price);
  if (product.price_verified === true && Number.isFinite(amount) && amount > 0) {
    return `<span class="product-price">${formatPrice(amount)}</span>`;
  }
  if (product.is_demo_price === true && Number.isFinite(amount) && amount > 0) {
    return `<span class="product-price">${formatPrice(amount)}<small class="demo-price-label">${text("demoPriceLabel")}</small></span>`;
  }
  return `<span class="product-price placeholder">${text("priceNotProvided")}</span>`;
}

function recommendationReasonText(reasonCode) {
  const keys = {
    seed_match: "recommendationReasonSeed",
    crop_and_text_match: "recommendationReasonCropText",
    product_text_match: "recommendationReasonText",
    fertilizer_category: "recommendationReasonFertilizer",
  };
  return text(keys[reasonCode] || "recommendationReasonText");
}

function renderRecommendationResults() {
  const container = $("recommendationResults");
  if (!recommendationData) return;
  container.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "recommendation-results-heading";
  const title = document.createElement("h3");
  title.textContent = text("recommendationResultsHeading");
  const mode = document.createElement("span");
  mode.className = "recommendation-mode";
  mode.textContent = text(recommendationData.mode === "ai" ? "recommendationModeAI" : "recommendationModeRules");
  heading.append(title, mode);
  container.append(heading);

  if (!recommendationData.products.length) {
    const empty = document.createElement("div");
    empty.className = "recommendation-message";
    const message = document.createElement("strong");
    message.textContent = text("recommendationNoMatches");
    const hint = document.createElement("p");
    hint.textContent = text("recommendationNoMatchesHint");
    empty.append(message, hint);
    container.append(empty);
    return;
  }

  const grid = document.createElement("div");
  grid.className = "recommendation-grid";
  recommendationData.products.forEach(product => {
    const card = document.createElement("article");
    card.className = "recommendation-card";
    const imageWrap = document.createElement("div");
    imageWrap.className = "product-image-wrap";
    const image = document.createElement("img");
    image.className = "product-image";
    image.src = productImage(product);
    image.dataset.fallbackImage = categoryPlaceholder(product.category);
    image.alt = productImageAlt(product);
    image.loading = "lazy";
    const imageLabel = document.createElement("span");
    imageLabel.className = "product-label";
    imageLabel.textContent = text("illustrativeImage");
    imageWrap.append(image, imageLabel);

    const body = document.createElement("div");
    body.className = "recommendation-card-body";
    const category = document.createElement("span");
    category.className = "product-category";
    category.textContent = getCategoryName(product.category);
    const name = document.createElement("h4");
    name.textContent = product.name;
    const description = document.createElement("p");
    description.textContent = getProductDescription(product) || text("noGuidance");

    const meta = document.createElement("div");
    meta.className = "recommendation-card-meta";
    const price = document.createElement("span");
    price.className = product.price_verified === true || product.is_demo_price
      ? "product-price"
      : "product-price placeholder";
    price.textContent = product.price_verified === true || product.is_demo_price
      ? `${formatPrice(product.price)}${product.is_demo_price ? ` · ${text("demoPriceLabel")}` : ""}`
      : text("priceNotProvided");
    const availability = document.createElement("span");
    availability.className = "stock-status";
    availability.textContent = `${text("recommendationInStock")} · ${Number(product.stock).toLocaleString(lang === "te" ? "te-IN" : "en-IN")}`;
    meta.append(price, availability);

    const reason = document.createElement("p");
    reason.className = "recommendation-reason";
    reason.textContent = recommendationReasonText(product.reason_code);
    const actions = document.createElement("div");
    actions.className = "recommendation-actions";
    const details = document.createElement("button");
    details.type = "button";
    details.className = "details-button";
    details.dataset.recommendationDetails = String(product.id);
    details.textContent = text("viewDetails");
    const add = document.createElement("button");
    add.type = "button";
    add.className = "add-cart-button";
    add.dataset.recommendationAdd = String(product.id);
    add.textContent = text("addToCart");
    actions.append(details, add);
    body.append(category, name, description, meta, reason, actions);
    card.append(imageWrap, body);
    grid.append(card);
  });
  container.append(grid);
}

function showRecommendationError(key) {
  recommendationData = null;
  const container = $("recommendationResults");
  container.replaceChildren();
  const message = document.createElement("div");
  message.className = "recommendation-message recommendation-error";
  message.setAttribute("role", "alert");
  message.textContent = text(key);
  container.append(message);
}

function formatDiseaseClass(label) {
  const health = label.health === "healthy"
    ? text("diseaseHealthHealthy")
    : text("diseaseHealthDiseased");
  return `${label.crop}: ${lang === "te" ? label.label_te : label.label_en} (${health})`;
}

function renderDiseaseModelStatus() {
  const status = $("diseaseModelStatus");
  const supported = $("diseaseSupportedClasses");
  status.dataset.state = diseaseModelInfo?.status === "ready"
    ? "ready"
    : diseaseModelInfo?.status === "model_invalid"
      ? "invalid"
      : "unavailable";
  if (!diseaseModelInfo) {
    status.textContent = text("diseaseModelUnavailable");
    supported.textContent = text("diseaseClassesUnavailable");
    $("diseaseCrop").setAttribute("list", "");
    $("diseaseSubmit").disabled = true;
    return;
  }
  const statusKeys = {
    ready: "diseaseModelReady",
    runtime_unavailable: "diseaseModelRuntimeMissing",
    model_invalid: "diseaseModelInvalid",
    model_unavailable: "diseaseModelUnavailable",
  };
  status.textContent = text(statusKeys[diseaseModelInfo.status] || "diseaseModelUnavailable");
  status.setAttribute("data-i18n", statusKeys[diseaseModelInfo.status] || "diseaseModelUnavailable");
  const classRows = diseaseModelInfo.classes || [];
  supported.textContent = classRows.length
    ? classRows.map(formatDiseaseClass).join(" · ")
    : text("diseaseClassesUnavailable");
  const cropInput = $("diseaseCrop");
  cropInput.setAttribute("list", "diseaseSupportedCropOptions");
  let list = $("diseaseSupportedCropOptions");
  if (!list) {
    list = document.createElement("datalist");
    list.id = "diseaseSupportedCropOptions";
    cropInput.insertAdjacentElement("afterend", list);
  }
  list.replaceChildren();
  [...new Set(classRows.map(item => item.crop))].forEach(crop => {
    const option = document.createElement("option");
    option.value = crop;
    list.append(option);
  });
  $("diseaseSubmit").disabled = diseaseModelInfo.status !== "ready";
}

async function loadDiseaseModelInfo() {
  try {
    const response = await fetch("/api/disease");
    if (!response.ok) throw new Error(`Disease model status failed (${response.status})`);
    const info = await response.json();
    if (!info || typeof info !== "object" || !Array.isArray(info.classes)) {
      throw new Error("Disease model status response was invalid");
    }
    diseaseModelInfo = info;
    renderDiseaseModelStatus();
  } catch (error) {
    console.error("Could not load plant disease model status:", error);
    diseaseModelInfo = null;
    renderDiseaseModelStatus();
  }
}

function clearDiseaseImage() {
  if (diseasePreviewUrl) {
    URL.revokeObjectURL(diseasePreviewUrl);
    diseasePreviewUrl = null;
  }
  $("diseaseImage").value = "";
  $("diseaseImagePreview").hidden = true;
  $("diseasePreviewImage").removeAttribute("src");
}

function showDiseaseResult(payload) {
  const container = $("diseaseResult");
  container.replaceChildren();
  const card = document.createElement("section");
  card.className = "disease-result-card";
  const heading = document.createElement("h3");
  heading.textContent = payload.inconclusive
    ? text("diseaseInconclusive")
    : text("diseaseResultHeading");
  card.append(heading);
  if (payload.prediction) {
    const result = document.createElement("p");
    result.textContent = `${payload.prediction.label} — ${(payload.prediction.confidence * 100).toFixed(1)}% ${text("diseaseConfidenceLabel")}`;
    card.append(result);
    if (Array.isArray(payload.top_predictions) && payload.top_predictions.length > 1) {
      const list = document.createElement("ul");
      payload.top_predictions.forEach(item => {
        const row = document.createElement("li");
        row.textContent = `${item.label} — ${(item.confidence * 100).toFixed(1)}%`;
        list.append(row);
      });
      card.append(list);
    }
  }
  if (payload.message) {
    const message = document.createElement("p");
    message.textContent = payload.message;
    card.append(message);
  }
  if (payload.disclaimer) {
    const disclaimer = document.createElement("p");
    disclaimer.textContent = payload.disclaimer;
    card.append(disclaimer);
  }
  container.append(card);
}

async function submitDiseaseImage(event) {
  event.preventDefault();
  const file = $("diseaseImage").files[0];
  if (!file) {
    showDiseaseError("diseaseImageRequired");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showDiseaseError("diseaseImageTooLarge");
    return;
  }
  if (!/\.(jpe?g|png)$/i.test(file.name)) {
    showDiseaseError("diseaseImageInvalid");
    return;
  }
  if (!diseaseModelInfo || diseaseModelInfo.status !== "ready") {
    showDiseaseError("diseaseNoModel");
    return;
  }
  if (diseaseRequestController) diseaseRequestController.abort();
  const controller = new AbortController();
  diseaseRequestController = controller;
  const submit = $("diseaseSubmit");
  submit.disabled = true;
  $("diseaseLoading").hidden = false;
  $("diseaseResult").replaceChildren();
  const formData = new FormData();
  formData.append("image", file);
  formData.append("crop", $("diseaseCrop").value.trim());
  formData.append("lang", lang);
  try {
    const response = await fetch("/api/disease", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    const result = await response.json();
    if (!result || typeof result !== "object") throw new Error("invalid_response");
    if (!response.ok) {
      const errorKeys = {
        image_required: "diseaseImageRequired",
        image_too_large: "diseaseImageTooLarge",
        invalid_image: "diseaseImageInvalid",
        invalid_image_dimensions: "diseaseImageDimensions",
        unsupported_file_type: "diseaseImageInvalid",
        unsupported_image_format: "diseaseImageInvalid",
        image_format_mismatch: "diseaseImageInvalid",
        unsupported_crop: "diseaseUnsupportedCrop",
        model_unavailable: "diseaseNoModel",
        inference_failed: "diseaseUnavailable",
      };
      showDiseaseError(text(errorKeys[result.code] || "diseaseUnavailable"));
      return;
    }
    showDiseaseResult(result);
  } catch (error) {
    if (!controller.signal.aborted) {
      showDiseaseError(error instanceof TypeError ? "diseaseNetworkError" : "diseaseUnavailable");
    }
  } finally {
    if (diseaseRequestController === controller) {
      diseaseRequestController = null;
      $("diseaseLoading").hidden = true;
      submit.disabled = !diseaseModelInfo || diseaseModelInfo.status !== "ready";
    }
  }
}

function showDiseaseError(key) {
  const container = $("diseaseResult");
  container.replaceChildren();
  const error = document.createElement("div");
  error.className = "disease-result-card disease-result-error";
  error.setAttribute("role", "alert");
  error.textContent = text(key);
  container.append(error);
}

async function submitRecommendations(event) {
  event.preventDefault();
  const cropInput = $("recommendationCrop");
  const stageInput = $("recommendationStage");
  const questionInput = $("recommendationQuestion");
  const otherCropInput = $("recommendationOtherCrop");
  cropInput.setCustomValidity(cropInput.value ? "" : text("recommendationCropFieldRequired"));
  stageInput.setCustomValidity(stageInput.value ? "" : text("recommendationStageFieldRequired"));
  questionInput.setCustomValidity(questionInput.value.trim() ? "" : text("recommendationQuestionFieldRequired"));
  otherCropInput.setCustomValidity(
    cropInput.value !== "other" || otherCropInput.value.trim()
      ? ""
      : text("recommendationOtherCropRequired")
  );
  if (!$("recommendationForm").reportValidity()) return;
  if (recommendationRequestController) recommendationRequestController.abort();
  const controller = new AbortController();
  recommendationRequestController = controller;
  const submit = $("recommendationSubmit");
  submit.disabled = true;
  $("recommendationResults").setAttribute("aria-busy", "true");
  const loading = document.createElement("div");
  loading.className = "recommendation-message";
  loading.textContent = text("recommendationLoading");
  $("recommendationResults").replaceChildren(loading);
  const payload = {
    crop: $("recommendationCrop").value,
    other_crop: $("recommendationOtherCrop").value.trim(),
    stage: $("recommendationStage").value,
    location: $("recommendationLocation").value.trim(),
    soil: $("recommendationSoil").value.trim(),
    question: $("recommendationQuestion").value.trim(),
    lang: $("recommendationLanguage").value,
  };
  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const result = await response.json();
    if (!result || typeof result !== "object") throw new Error("invalid_response");
    if (!response.ok) {
      const errorKeys = {
        rate_limited: "recommendationRateLimited",
        provider_unavailable: "recommendationProviderUnavailable",
        invalid_crop: "recommendationInvalidInput",
        invalid_stage: "recommendationInvalidInput",
        invalid_language: "recommendationInvalidInput",
        invalid_input: "recommendationInvalidInput",
        input_too_long: "recommendationInvalidInput",
        question_required: "recommendationInvalidInput",
        other_crop_required: "recommendationOtherCropRequired",
        request_too_large: "recommendationInvalidInput",
      };
      showRecommendationError(text(errorKeys[result.code] || "recommendationUnavailable"));
      return;
    }
    if (!Array.isArray(result.products) || !["ai", "rule_based"].includes(result.mode)) {
      throw new Error("invalid_response");
    }
    recommendationData = result;
    renderRecommendationResults();
  } catch (error) {
    if (!controller.signal.aborted) {
      showRecommendationError("recommendationUnavailable");
    }
  } finally {
    if (recommendationRequestController === controller) {
      recommendationRequestController = null;
      submit.disabled = false;
      $("recommendationResults").setAttribute("aria-busy", "false");
    }
  }
}

async function addRecommendationToCart(id) {
  if (!recommendationData?.products.some(product => Number(product.id) === id)) return;
  if (!getProduct(id)) {
    try {
      const response = await fetch("/api/products");
      if (!response.ok) throw new Error(`Catalogue request failed (${response.status})`);
      const rows = await response.json();
      if (!Array.isArray(rows)) throw new Error("Catalogue response was invalid");
      products = rows;
      renderProducts(products);
    } catch (error) {
      console.error("Could not load recommendation product for cart:", error);
      showCartTranslation("productUnavailable", true);
      return;
    }
  }
  addToCart(id);
}

function setLoading(isLoading) {
  $("productGrid").setAttribute("aria-busy", String(isLoading));
  if (isLoading) $("resultCount").textContent = text("loading");
}

async function loadProducts() {
  if (requestController) requestController.abort();
  const controller = new AbortController();
  requestController = controller;
  const params = new URLSearchParams({
    category,
    search: lang === "te" ? "" : $("search").value.trim()
  });
  setLoading(true);
  try {
    const response = await fetch(`/api/products?${params}`, {signal: controller.signal});
    if (requestController !== controller) return;
    if (!response.ok) throw new Error(`Catalogue request failed (${response.status})`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("Catalogue response was not a product list");
    products = data;
    renderProducts(products);
    renderCart();
  } catch (error) {
    if (error.name === "AbortError" || requestController !== controller) return;
    console.error("Unable to load the product catalogue:", error);
    $("productGrid").setAttribute("aria-busy", "false");
    $("resultCount").textContent = "";
    $("productGrid").innerHTML = `<div class="empty-state"><span aria-hidden="true">!</span><h3>${text("catalogueUnavailable")}</h3><button class="details-button" id="retryProducts" type="button">${text("retry")}</button></div>`;
    $("retryProducts").addEventListener("click", loadProducts, {once: true});
    renderCart();
  }
}

function normalizeIndianPhone(phone) {
  let normalized = phone.replace(/[\s().-]/g, "");
  if (normalized.startsWith("+91")) normalized = normalized.slice(3);
  else if (normalized.startsWith("91") && normalized.length === 12) normalized = normalized.slice(2);
  else if (normalized.startsWith("0") && normalized.length === 11) normalized = normalized.slice(1);
  return /^[6-9]\d{9}$/.test(normalized) ? normalized : null;
}

async function submitOrder(event) {
    event.preventDefault();
    $("orderResult").textContent = "";
    if (!cart.length) {
      setCartTranslation("emptyCartCheckout", true);
      return;
    }
    if (!$("checkoutForm").reportValidity()) return;
    if (!$("customerName").value.trim() || !$("customerAddress").value.trim()) {
      setCartTranslation("checkoutRequired", true);
      return;
    }

    const phone = normalizeIndianPhone($("customerPhone").value.trim());
    if (!phone) {
      $("customerPhone").setCustomValidity(text("phoneInvalid"));
      $("customerPhone").reportValidity();
      $("customerPhone").setCustomValidity("");
      setCartTranslation("phoneInvalid", true);
      return;
    }

    const unavailableItem = cart.find(item => {
      const product = getProduct(item.id);
      return !product || item.quantity < 1 || item.quantity > Number(product.stock) ||
        product.price_verified !== true || !Number.isFinite(Number(product.price)) || Number(product.price) <= 0;
    });
    if (unavailableItem) {
      const product = getProduct(unavailableItem.id);
      setCartTranslation(product && (Number(product.price) <= 0 || product.price_verified !== true)
        ? "priceMustBeConfirmed"
        : "cartNeedsAttention", true);
      renderCart();
      return;
    }

    const payload = {
      name: $("customerName").value.trim(),
      phone,
      address: $("customerAddress").value.trim(),
      notes: $("orderNotes").value.trim(),
      items: cart.map(item => ({id: item.id, quantity: item.quantity}))
    };
    const submitButton = $("checkoutSubmit");
    submitButton.disabled = true;
    submitButton.textContent = text("submittingOrder");
    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) {
        const messageKey = result.code === "invalid_phone" ? "phoneInvalid"
          : result.code === "order_save_failed" ? "orderSaveFailed"
          : "orderValidationFailed";
        const validationMessage = result.code === "insufficient_stock" ? "cartNeedsAttention"
          : result.code === "product_unavailable" ? "productUnavailable"
          : result.code === "price_unavailable" || result.code === "invalid_product_price" ? "priceMustBeConfirmed"
          : messageKey;
        setCartTranslation(validationMessage, true);
        if (result.code === "insufficient_stock" || result.code === "product_unavailable") {
          loadProducts();
        }
        return;
      }

      cart = [];
      saveCart();
      renderCart();
      setCartMessage("");
      $("checkoutForm").reset();
      lastOrderReference = result.order_reference;
      $("orderResult").textContent = `${text("orderConfirmation")} ${text("orderReference")}: ${lastOrderReference}. ${text("orderPaymentReminder")}`;
      $("checkoutSubmit").disabled = true;
      loadProducts();
    } catch (error) {
      console.error("Unable to submit the order:", error);
      setCartTranslation("orderSaveFailed", true);
    } finally {
      renderCart();
      submitButton.textContent = text("confirmOrder");
  }
}

function showProductDetails(id) {
  const product = products.find(item => Number(item.id) === id);
  if (!product) return;
  dialogProductId = id;

  const hasPrice = (product.price_verified === true || product.is_demo_price === true) &&
    Number.isFinite(Number(product.price)) && Number(product.price) > 0;
  const price = hasPrice
    ? `${formatPrice(product.price)}${product.is_demo_price ? ` · ${text("demoPriceLabel")}` : ""}`
    : text("priceConfirm");
  const guidance = lang === "te" ? product.guidance_te : product.guidance_en;
  const brand = product.brand_verified === true ? String(product.brand || "").trim() : "";
  $("dialogClose").setAttribute("aria-label", text("closeDetails"));
  $("dialogContent").innerHTML = `<img class="dialog-image" src="${productImage(product)}" ${productImageFallbackAttribute(product)} alt="${escapeHtml(productImageAlt(product))}">
    <div class="dialog-body">
      <span class="product-category" aria-label="${text("productCategory")}">${escapeHtml(getCategoryName(product.category))}</span>
      <h2 id="dialogTitle">${escapeHtml(product.name)}</h2>
      ${brand ? `<p class="product-brand">${text("brandLabel")}: ${escapeHtml(brand)}</p>` : ""}
      <p>${escapeHtml(getProductDescription(product))}</p>
      <div class="dialog-price">${text("priceLabel")}: ${price}</div>
      <p class="dialog-pack-size">${text("packSizeLabel")}: ${escapeHtml(getUnitName(product.unit || ""))}</p>
      <span class="stock-status${product.stock_verified !== true ? " pending-status" : Number(product.stock) > 0 ? "" : " out-of-stock"}">${product.stock_verified !== true ? text("availabilityUnconfirmed") : Number(product.stock) > 0 ? `${text("inStock")} · ${Number(product.stock).toLocaleString(lang === "te" ? "te-IN" : "en-IN")}` : text("outOfStock")}</span>
      <div class="dialog-guidance"><strong>${text("productGuidance")}</strong>${escapeHtml(guidance || text("noGuidance"))}<br><br>${text("confirmLabel")}</div>
    </div>`;
  if (!$("detailsDialog").open) $("detailsDialog").showModal();
}

function addAssistantMessage(role, content, mode = null) {
  const message = document.createElement("div");
  message.className = `assistant-message assistant-message-${role}`;
  const label = document.createElement("span");
  label.className = "assistant-message-label";
  label.dataset.chatRole = role;
  label.textContent = text(role === "user" ? "assistantUserLabel" : "assistantLabel");
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  message.append(label, paragraph);
  if (mode) {
    const modeLabel = document.createElement("small");
    modeLabel.className = "assistant-mode-label";
    modeLabel.dataset.chatMode = mode;
    modeLabel.textContent = text(mode === "ai" ? "assistantModeAI" : "assistantModeFallback");
    message.append(modeLabel);
  }
  $("assistantMessages").append(message);
  $("assistantMessages").scrollTop = $("assistantMessages").scrollHeight;
}

function resetAssistantChat() {
  if (assistantRequestController) {
    assistantRequestController.abort();
    assistantRequestController = null;
  }
  $("assistantLoading").hidden = true;
  $("assistantSend").disabled = false;
  $("assistantInput").value = "";
  $("assistantMessages").replaceChildren();
  const welcome = document.createElement("div");
  welcome.className = "assistant-message assistant-response";
  const label = document.createElement("span");
  label.className = "assistant-message-label";
  label.dataset.i18n = "assistantLabel";
  label.textContent = text("assistantLabel");
  const paragraph = document.createElement("p");
  paragraph.dataset.i18n = "assistantWelcome";
  paragraph.textContent = text("assistantWelcome");
  welcome.append(label, paragraph);
  $("assistantMessages").append(welcome);
}

async function submitAssistantQuestion(event) {
  event.preventDefault();
  const input = $("assistantInput");
  const message = input.value.trim();
  if (!message) {
    input.setCustomValidity(text("assistantErrorRequired"));
    input.reportValidity();
    return;
  }
  input.setCustomValidity("");
  addAssistantMessage("user", message);
  input.value = "";
  $("assistantLoading").hidden = false;
  $("assistantSend").disabled = true;
  const controller = new AbortController();
  assistantRequestController = controller;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message, lang}),
      signal: controller.signal,
    });
    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new Error(text("assistantErrorGeneral"));
    }
    if (!payload || typeof payload !== "object") {
      throw new Error(text("assistantErrorGeneral"));
    }
    if (!response.ok) {
      const errorKeys = {
        message_required: "assistantErrorRequired",
        message_too_long: "assistantErrorTooLong",
        rate_limited: "assistantErrorRateLimited",
        provider_unavailable: "assistantErrorUnavailable",
        provider_timeout: "assistantErrorTimeout",
      };
      throw new Error(text(errorKeys[payload.code] || "assistantErrorGeneral"));
    }
    if (typeof payload.answer !== "string" || !payload.answer.trim()) {
      throw new Error(text("assistantErrorGeneral"));
    }
    addAssistantMessage("response", payload.answer, payload.mode === "ai" ? "ai" : "fallback");
  } catch (error) {
    if (!controller.signal.aborted) {
      addAssistantMessage(
        "response",
        error instanceof TypeError ? text("assistantErrorNetwork") : (error.message || text("assistantErrorGeneral"))
      );
    }
  } finally {
    if (assistantRequestController === controller) {
      assistantRequestController = null;
      $("assistantLoading").hidden = true;
      $("assistantSend").disabled = false;
    }
  }
}

function applyLanguage(language, persist = true) {
  const previousCartMessage = cartMessageState;
  lang = language === "te" ? "te" : "en";
  document.documentElement.lang = lang;
  $("langToggle").value = lang;
  const introLanguagePicker = $("introLanguageToggle");
  if (introLanguagePicker) introLanguagePicker.value = lang;
  document.querySelectorAll("[data-i18n]").forEach(element => {
    const key = element.dataset.i18n;
    if (translations[lang].ui[key]) element.textContent = translations[lang].ui[key];
  });
  document.querySelectorAll("[data-i18n-aria]").forEach(element => {
    const key = element.dataset.i18nAria;
    if (translations[lang].ui[key]) element.setAttribute("aria-label", translations[lang].ui[key]);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
    const key = element.dataset.i18nPlaceholder;
    if (translations[lang].ui[key]) element.setAttribute("placeholder", translations[lang].ui[key]);
  });
  document.querySelectorAll("[data-chat-role]").forEach(element => {
    element.textContent = text(element.dataset.chatRole === "user" ? "assistantUserLabel" : "assistantLabel");
  });
  document.querySelectorAll("[data-chat-mode]").forEach(element => {
    element.textContent = text(element.dataset.chatMode === "ai" ? "assistantModeAI" : "assistantModeFallback");
  });
  document.title = lang === "te"
    ? "జగన్ ఫెర్టిలైజర్ | వ్యవసాయ అవసరాలు"
    : "JAGAN FERTILIZER | Farm essentials, made easier";
  document.querySelector('meta[name="description"]').content = lang === "te"
    ? "జగన్ ఫెర్టిలైజర్ వ్యవసాయ ఉత్పత్తుల జాబితాను చూడండి."
    : "Browse the JAGAN FERTILIZER catalogue of agricultural products.";
  $("activeCategory").textContent = translations[lang].categories[category];
  $("recommendationLanguage").value = lang;
  if (persist) saveLanguage(lang);
  setCartMessage("");
  if (requestController) {
    loadProducts();
  } else {
    renderProducts(products);
  }
  renderCart();
  if (previousCartMessage) {
    setCartTranslation(
      previousCartMessage.key,
      previousCartMessage.isError,
      previousCartMessage.values
    );
  }
  if (lastOrderReference) {
    $("orderResult").textContent = `${text("orderConfirmation")} ${text("orderReference")}: ${lastOrderReference}. ${text("orderPaymentReminder")}`;
  }
  if ($("detailsDialog").open && dialogProductId !== null) {
    showProductDetails(dialogProductId);
  }
  if (recommendationData) renderRecommendationResults();
  renderDiseaseModelStatus();
}

document.querySelectorAll(".category-card").forEach(button => {
  button.addEventListener("click", () => {
    category = button.dataset.category;
    document.querySelectorAll(".category-card").forEach(card => {
      const active = card === button;
      card.classList.toggle("active", active);
      card.setAttribute("aria-pressed", String(active));
    });
    $("activeCategory").textContent = translations[lang].categories[category];
    $("shop").scrollIntoView({behavior: "smooth", block: "start"});
    loadProducts();
  });
});

document.addEventListener("error", event => {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || !image.dataset.fallbackImage) return;
  if (image.src.endsWith(image.dataset.fallbackImage)) return;
  image.src = image.dataset.fallbackImage;
}, true);

$("productGrid").addEventListener("click", event => {
  const button = event.target.closest("[data-product-id]");
  if (button) showProductDetails(Number(button.dataset.productId));
  const addButton = event.target.closest("[data-add-product]");
  if (addButton) addToCart(Number(addButton.dataset.addProduct));
});
$("recommendationForm").addEventListener("submit", submitRecommendations);
$("recommendationCrop").addEventListener("change", () => {
  const isOther = $("recommendationCrop").value === "other";
  $("otherCropField").hidden = !isOther;
  $("recommendationOtherCrop").required = isOther;
  $("recommendationCrop").setCustomValidity("");
  $("recommendationOtherCrop").setCustomValidity("");
  if (!isOther) $("recommendationOtherCrop").value = "";
});
$("recommendationForm").addEventListener("input", event => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    event.target.setCustomValidity("");
  }
});
$("recommendationForm").addEventListener("change", event => {
  if (event.target instanceof HTMLSelectElement) event.target.setCustomValidity("");
});
$("recommendationResults").addEventListener("click", event => {
  const details = event.target.closest("[data-recommendation-details]");
  if (details) showProductDetails(Number(details.dataset.recommendationDetails));
  const add = event.target.closest("[data-recommendation-add]");
  if (add) addRecommendationToCart(Number(add.dataset.recommendationAdd));
});
$("cartItems").addEventListener("click", event => {
  const quantityButton = event.target.closest("[data-quantity-change]");
  if (quantityButton) {
    changeCartQuantity(Number(quantityButton.dataset.itemId), Number(quantityButton.dataset.quantityChange));
    return;
  }
  const removeButton = event.target.closest("[data-remove-item]");
  if (removeButton) removeCartItem(Number(removeButton.dataset.removeItem));
});
$("cartOpen").addEventListener("click", () => {
  setCartMessage("");
  renderCart();
  $("cartDialog").showModal();
});
$("cartClose").addEventListener("click", () => $("cartDialog").close());
$("cartDialog").addEventListener("click", event => {
  if (event.target === $("cartDialog")) $("cartDialog").close();
});
$("checkoutForm").addEventListener("submit", submitOrder);
$("assistantForm").addEventListener("submit", submitAssistantQuestion);
$("assistantClear").addEventListener("click", resetAssistantChat);
$("assistantInput").addEventListener("input", event => event.target.setCustomValidity(""));
$("diseaseImage").addEventListener("change", () => {
  const file = $("diseaseImage").files[0];
  if (!file) {
    clearDiseaseImage();
    return;
  }
  if (diseasePreviewUrl) URL.revokeObjectURL(diseasePreviewUrl);
  diseasePreviewUrl = URL.createObjectURL(file);
  $("diseasePreviewImage").src = diseasePreviewUrl;
  $("diseasePreviewImage").alt = `${text("illustrativeImage")}: ${file.name}`;
  $("diseaseImagePreview").hidden = false;
  $("diseaseResult").replaceChildren();
});
$("diseaseClearImage").addEventListener("click", clearDiseaseImage);
$("diseaseForm").addEventListener("submit", submitDiseaseImage);
$("search").addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadProducts, 180);
});
document.addEventListener("keydown", event => {
  const target = event.target;
  if (event.key === "/" && !event.ctrlKey && !event.metaKey &&
      !["INPUT", "TEXTAREA", "BUTTON", "SELECT"].includes(target.tagName) &&
      !$("detailsDialog").open) {
    event.preventDefault();
    $("search").focus();
  }
});
$("langToggle").addEventListener("change", event => applyLanguage(event.target.value));
$("introLanguageToggle").addEventListener("change", event => applyLanguage(event.target.value));
$("dialogClose").addEventListener("click", () => $("detailsDialog").close());
$("detailsDialog").addEventListener("close", () => {
  dialogProductId = null;
});
$("detailsDialog").addEventListener("click", event => {
  if (event.target === $("detailsDialog")) $("detailsDialog").close();
});
$("menuToggle").addEventListener("click", () => {
  const menu = $("primaryNav");
  const open = menu.classList.toggle("open");
  $("menuToggle").setAttribute("aria-expanded", String(open));
  $("menuToggle").setAttribute("aria-label", text(open ? "menuClose" : "menuOpen"));
});
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    $("primaryNav").classList.remove("open");
    $("menuToggle").setAttribute("aria-expanded", "false");
    $("menuToggle").setAttribute("aria-label", text("menuOpen"));
  });
});
$("year").textContent = new Date().getFullYear();
applyLanguage(lang, false);
renderCart();
loadProducts();
loadDiseaseModelInfo();

function finishIntro() {
  const screen = $("introScreen");
  if (!screen || screen.getAttribute("aria-hidden") === "true") return;
  if (introTimer !== null) {
    window.clearTimeout(introTimer);
    introTimer = null;
  }
  $("siteContent").inert = false;
  $("homeTitle").focus({preventScroll: true});
  screen.classList.add("intro-exit");
  screen.setAttribute("aria-hidden", "true");
  document.body.classList.remove("intro-visible");
  window.setTimeout(() => screen.remove(), 500);
}

function startIntro() {
  const replayRequested = new URLSearchParams(window.location.search).get("replay-intro") === "1";
  let alreadySeen = false;
  try {
    alreadySeen = sessionStorage.getItem(INTRO_SESSION_KEY) === "true";
    if (!alreadySeen || replayRequested) {
      sessionStorage.setItem(INTRO_SESSION_KEY, "true");
    }
  } catch (error) {
    console.warn("Could not read the intro session preference:", error);
  }
  if (alreadySeen && !replayRequested) {
    $("introScreen").remove();
    return;
  }

  const screen = $("introScreen");
  document.body.classList.add("intro-visible");
  $("siteContent").inert = true;
  screen.setAttribute("aria-hidden", "false");
  $("introSkip").focus({preventScroll: true});
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  introTimer = window.setTimeout(finishIntro, reducedMotion ? 900 : 3600);
}

$("introSkip").addEventListener("click", finishIntro);
document.addEventListener("keydown", event => {
  const screen = $("introScreen");
  if (!screen || screen.getAttribute("aria-hidden") !== "false") return;
  if (event.key === "Escape") {
    finishIntro();
    return;
  }
  if (event.key === "Tab") {
    const first = $("introLanguageToggle");
    const last = $("introSkip");
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});
startIntro();
