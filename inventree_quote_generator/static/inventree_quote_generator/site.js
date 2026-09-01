function parseCatalog(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
        return JSON.parse(node.textContent || "[]");
    } catch {
        return [];
    }
}

function field(line, suffix) {
    return line.querySelector(`[name$="-${suffix}"]`);
}

function visibleLines(container) {
    return Array.from(container.querySelectorAll("[data-line-form]")).filter(
        (line) => !line.classList.contains("is-deleted")
    );
}

function setPriceStatus(line, message, state = "") {
    const status = line.querySelector("[data-price-status]");
    if (!status) return;
    status.textContent = message;
    status.classList.remove("found", "manual", "loading");
    if (state) status.classList.add(state);
}

function initializeQuoteEditor(page) {
    const form = page.querySelector("[data-quote-form]");
    const lineContainer = page.querySelector("[data-line-items]");
    const template = page.querySelector("[data-empty-line-template]");
    const totalForms = page.querySelector('[name="lines-TOTAL_FORMS"]');
    const customerSelect = form?.querySelector('[name="customer"]');
    const quoteCurrency = form?.querySelector('[name="currency"]');
    const priceApi = form?.dataset.priceApi;
    if (!form || !lineContainer || !template || !totalForms) return;

    const parts = new Map(parseCatalog("quote-parts-catalog").map((part) => [String(part.pk), part]));
    const customers = new Map(
        parseCatalog("quote-customers-catalog").map((customer) => [String(customer.pk), customer])
    );
    let submitting = false;
    let dirty = false;

    function updateLineNumbers() {
        visibleLines(lineContainer).forEach((line, index) => {
            const number = line.querySelector("[data-line-number]");
            if (number) number.textContent = String(index + 1);
        });
    }

    function updateTotals() {
        const currency = String(quoteCurrency?.value || "CAD").toUpperCase();
        let total = 0;
        let priced = 0;
        let mixed = false;
        visibleLines(lineContainer).forEach((line) => {
            const quantity = Number(field(line, "quantity")?.value);
            const price = Number(field(line, "unit_price")?.value);
            const lineCurrency = String(field(line, "currency")?.value || currency).toUpperCase();
            if (Number.isFinite(quantity) && Number.isFinite(price)) {
                priced += 1;
                total += quantity * price;
                if (lineCurrency !== currency) mixed = true;
            }
        });
        const countNode = page.querySelector("[data-priced-count]");
        const totalNode = page.querySelector("[data-working-total]");
        if (countNode) countNode.textContent = String(priced);
        if (totalNode) {
            if (!priced) {
                totalNode.textContent = "—";
            } else if (mixed) {
                totalNode.textContent = "Mixed currencies";
            } else {
                try {
                    totalNode.textContent = new Intl.NumberFormat(undefined, {
                        style: "currency",
                        currency,
                        maximumFractionDigits: 2
                    }).format(total);
                } catch {
                    totalNode.textContent = `${currency} ${total.toFixed(2)}`;
                }
            }
        }
    }

    async function resolveLine(line, clearOnMiss = true) {
        const mode = field(line, "price_mode");
        const part = field(line, "part");
        const quantity = field(line, "quantity");
        const price = field(line, "unit_price");
        const currency = field(line, "currency");
        if (!mode || !part || !quantity || !price || !currency) return;

        if (mode.value !== "auto") {
            price.readOnly = false;
            setPriceStatus(line, "Manual price. Leave it blank if the quote should not show a price.", "manual");
            updateTotals();
            return;
        }
        price.readOnly = true;
        const customer = customerSelect?.value;
        if (!customer || !part.value || quantity.value === "") {
            setPriceStatus(line, "Choose a customer, part, and quantity to check pricing.");
            updateTotals();
            return;
        }

        if (line.priceAbort) line.priceAbort.abort();
        line.priceAbort = new AbortController();
        setPriceStatus(line, "Checking customer quantity pricing…", "loading");
        const params = new URLSearchParams({
            customer,
            part: part.value,
            quantity: quantity.value
        });
        try {
            const response = await fetch(`${priceApi}?${params}`, {
                credentials: "same-origin",
                signal: line.priceAbort.signal,
                headers: { Accept: "application/json" }
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.message || "Pricing could not be checked.");
            if (payload.found) {
                price.value = payload.unit_price ?? "";
                currency.value = payload.currency || quoteCurrency?.value || "CAD";
                price.readOnly = true;
                setPriceStatus(line, payload.source || "Customer-specific price applied.", "found");
            } else {
                mode.value = "manual";
                price.readOnly = false;
                if (clearOnMiss) price.value = "";
                currency.value = payload.currency || currency.value || quoteCurrency?.value || "CAD";
                setPriceStatus(line, `${payload.message || "No customer price found"} Enter a manual price.`, "manual");
                if (clearOnMiss) price.focus();
            }
        } catch (error) {
            if (error.name === "AbortError") return;
            mode.value = "manual";
            price.readOnly = false;
            setPriceStatus(line, `${error.message || "Pricing could not be checked."} Enter a manual price.`, "manual");
        } finally {
            updateTotals();
        }
    }

    function bindLine(line, newlyAdded = false) {
        const partSelect = field(line, "part");
        const quantity = field(line, "quantity");
        const mode = field(line, "price_mode");
        const price = field(line, "unit_price");
        const currency = field(line, "currency");
        const description = field(line, "description");
        const partNumber = field(line, "part_number");
        const remove = line.querySelector("[data-remove-line]");

        let timer;
        const scheduleResolve = (clearOnMiss = true) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => resolveLine(line, clearOnMiss), 180);
        };

        partSelect?.addEventListener("change", () => {
            const selected = parts.get(partSelect.value);
            if (selected) {
                if (!description.value || description.dataset.partFilled === "true") {
                    description.value = selected.name || selected.description || "";
                    description.dataset.partFilled = "true";
                }
                if (!partNumber.value || partNumber.dataset.partFilled === "true") {
                    partNumber.value = selected.IPN || "";
                    partNumber.dataset.partFilled = "true";
                }
            }
            dirty = true;
            scheduleResolve(true);
        });
        description?.addEventListener("input", () => { description.dataset.partFilled = "false"; });
        partNumber?.addEventListener("input", () => { partNumber.dataset.partFilled = "false"; });
        quantity?.addEventListener("input", () => { dirty = true; scheduleResolve(true); });
        mode?.addEventListener("change", () => { dirty = true; resolveLine(line, false); });
        price?.addEventListener("input", updateTotals);
        currency?.addEventListener("input", () => {
            currency.value = currency.value.toUpperCase();
            updateTotals();
        });
        remove?.addEventListener("click", () => {
            const deletion = field(line, "DELETE");
            if (deletion) deletion.checked = true;
            line.classList.add("is-deleted");
            dirty = true;
            if (!visibleLines(lineContainer).length) addLine();
            updateLineNumbers();
            updateTotals();
        });
        if (mode?.value === "auto" && price) price.readOnly = true;
        if (newlyAdded) {
            currency.value = quoteCurrency?.value || currency.value || "CAD";
            partSelect?.focus();
        }
    }

    function addLine() {
        const index = Number(totalForms.value || 0);
        const wrapper = document.createElement("div");
        wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index)).trim();
        const line = wrapper.firstElementChild;
        if (!line) return;
        lineContainer.appendChild(line);
        totalForms.value = String(index + 1);
        bindLine(line, true);
        updateLineNumbers();
        updateTotals();
        dirty = true;
    }

    page.querySelectorAll("[data-add-line]").forEach((button) => button.addEventListener("click", addLine));
    lineContainer.querySelectorAll("[data-line-form]").forEach((line) => bindLine(line));
    updateLineNumbers();
    updateTotals();

    customerSelect?.addEventListener("change", () => {
        const customer = customers.get(customerSelect.value);
        if (customer && quoteCurrency && !quoteCurrency.value) quoteCurrency.value = customer.currency || "CAD";
        visibleLines(lineContainer).forEach((line) => {
            if (field(line, "price_mode")?.value === "auto") resolveLine(line, true);
        });
        dirty = true;
    });
    quoteCurrency?.addEventListener("input", () => {
        quoteCurrency.value = quoteCurrency.value.toUpperCase();
        updateTotals();
    });

    form.addEventListener("input", () => { dirty = true; });
    form.addEventListener("change", () => { dirty = true; });
    form.addEventListener("submit", () => { submitting = true; });
    window.addEventListener("beforeunload", (event) => {
        if (!dirty || submitting) return;
        event.preventDefault();
        event.returnValue = "";
    });
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
            form.requestSubmit(form.querySelector('button[name="next"][value="stay"]'));
        }
    });
    page.querySelector("[data-confirm-delete]")?.addEventListener("click", (event) => {
        if (!window.confirm("Delete this quote permanently? This cannot be undone.")) {
            event.preventDefault();
        } else {
            submitting = true;
        }
    });

    const firstError = page.querySelector(".field-error, .error-banner");
    if (firstError) firstError.scrollIntoView({ behavior: "smooth", block: "center" });
}

const editor = document.querySelector("[data-quote-editor-page]");
if (editor) initializeQuoteEditor(editor);
