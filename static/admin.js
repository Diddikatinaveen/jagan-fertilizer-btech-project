(() => {
  const message = document.getElementById("adminMessage");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  const dictionary = window.JAGAN_TRANSLATIONS;

  function text(key) {
    const language = document.documentElement.lang === "te" ? "te" : "en";
    return dictionary[language].ui[key] || dictionary.en.ui[key] || key;
  }

  function collectProduct(form) {
    const fields = new FormData(form);
    return {
      name: fields.get("name"),
      category: fields.get("category"),
      brand: fields.get("brand"),
      brand_verified: form.elements.brand_verified.checked,
      description: fields.get("description"),
      description_te: fields.get("description_te"),
      price: Number(fields.get("price")),
      unit: fields.get("unit"),
      stock: Number(fields.get("stock")),
      stock_verified: form.elements.stock_verified.checked,
      image: fields.get("image"),
      guidance_en: fields.get("guidance_en"),
      guidance_te: fields.get("guidance_te"),
      active: form.elements.active.checked,
      price_verified: form.elements.price_verified.checked,
      registration_verified: form.elements.registration_verified.checked
    };
  }

  async function send(url, method, data) {
    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken
      },
      body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(text("adminSaveFailed"));
    return result;
  }

  document.querySelectorAll(".admin-product-form").forEach(form => {
    form.addEventListener("submit", async event => {
      event.preventDefault();
      message.textContent = "";
      try {
        const productId = form.dataset.productId;
        await send(
          productId ? `/api/admin/products/${productId}` : "/api/admin/products",
          productId ? "PATCH" : "POST",
          collectProduct(form)
        );
        message.classList.remove("error");
        message.textContent = text("adminSaveSuccess");
        if (!productId) form.reset();
        window.location.reload();
      } catch (error) {
        message.textContent = error.message || text("adminSaveFailed");
        message.classList.add("error");
      }
    });
  });

  document.querySelectorAll(".status-save").forEach(button => {
    button.addEventListener("click", async () => {
      const orderCard = button.closest("[data-order-id]");
      const status = orderCard.querySelector('[name="status"]').value;
      message.textContent = "";
      try {
        await send(`/api/admin/orders/${orderCard.dataset.orderId}/status`, "PATCH", {status});
        message.classList.remove("error");
        message.textContent = text("adminSaveSuccess");
        window.location.reload();
      } catch (error) {
        message.textContent = error.message || text("adminSaveFailed");
        message.classList.add("error");
      }
    });
  });
})();
