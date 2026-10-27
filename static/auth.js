(() => {
  const dictionary = window.JAGAN_TRANSLATIONS;
  const picker = document.getElementById("langToggle");
  let language = "en";

  try {
    language = localStorage.getItem("jagan-fertilizer-language") === "te" ? "te" : "en";
  } catch (error) {
    console.warn("Could not read the saved language preference:", error);
  }

  function text(key) {
    return dictionary[language].ui[key] || dictionary.en.ui[key] || key;
  }

  let refreshRegistrationValidity = () => {};

  function applyLanguage(value, persist = true) {
    language = value === "te" ? "te" : "en";
    document.documentElement.lang = language;
    if (picker) picker.value = language;
    document.querySelectorAll("[data-i18n]").forEach(element => {
      const translated = dictionary[language].ui[element.dataset.i18n];
      if (translated) element.textContent = translated;
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(element => {
      const translated = dictionary[language].ui[element.dataset.i18nAria];
      if (translated) element.setAttribute("aria-label", translated);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
      const translated = dictionary[language].ui[element.dataset.i18nPlaceholder];
      if (translated) element.setAttribute("placeholder", translated);
    });
    document.querySelectorAll("[data-status]").forEach(element => {
      const statusKey = `status${element.dataset.status}`;
      const translated = dictionary[language].ui[statusKey];
      if (translated) element.textContent = translated;
    });
    refreshRegistrationValidity();
    if (persist) {
      try {
        localStorage.setItem("jagan-fertilizer-language", language);
      } catch (error) {
        console.warn("Could not save the language preference:", error);
      }
    }
  }

  const form = document.querySelector(".account-form");
  if (form && form.dataset.mode === "register") {
    const nameField = form.elements.full_name;
    const identityField = form.elements.identity;
    const passwordField = form.elements.password;
    refreshRegistrationValidity = () => {
      if (nameField.validity.customError) {
        nameField.setCustomValidity(nameField.value.trim() ? "" : text("authNameInvalid"));
      };
      if (identityField.validity.customError) {
        const identity = identityField.value.trim();
        const compactPhone = identity.replace(/[\s().-]/g, "").replace(/^\+91/, "").replace(/^91(?=\d{10}$)/, "").replace(/^0(?=\d{10}$)/, "");
        const validEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(identity);
        const validPhone = /^[6-9]\d{9}$/.test(compactPhone);
        identityField.setCustomValidity(validEmail || validPhone ? "" : text("authIdentityInvalid"));
      }
      if (passwordField.validity.customError) {
        passwordField.setCustomValidity(passwordField.value.length >= 12 && passwordField.value.length <= 128
          ? ""
          : text("authPasswordInvalid"));
      }
    }
    form.addEventListener("submit", event => {
      const identity = identityField.value.trim();
      const compactPhone = identity.replace(/[\s().-]/g, "").replace(/^\+91/, "").replace(/^91(?=\d{10}$)/, "").replace(/^0(?=\d{10}$)/, "");
      const validEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(identity);
      const validPhone = /^[6-9]\d{9}$/.test(compactPhone);
      nameField.setCustomValidity(nameField.value.trim() ? "" : text("authNameInvalid"));
      identityField.setCustomValidity(validEmail || validPhone ? "" : text("authIdentityInvalid"));
      passwordField.setCustomValidity(passwordField.value.length >= 12 && passwordField.value.length <= 128
        ? ""
        : text("authPasswordInvalid"));
      if (!form.reportValidity()) event.preventDefault();
    });
    form.addEventListener("input", event => {
      if (event.target instanceof HTMLInputElement) event.target.setCustomValidity("");
    });
  }

  if (picker) picker.addEventListener("change", () => applyLanguage(picker.value));
  applyLanguage(language, false);
})();
