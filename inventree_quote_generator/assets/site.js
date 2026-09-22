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
    const partSearchApi = form?.dataset.partSearchApi;
    if (!form || !lineContainer || !template || !totalForms) return;

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
            const quantityValue = field(line, "quantity")?.value ?? "";
            const priceValue = field(line, "unit_price")?.value ?? "";
            const quantity = quantityValue === "" ? Number.NaN : Number(quantityValue);
            const price = priceValue === "" ? Number.NaN : Number(priceValue);
            const lineCurrency = String(field(line, "currency")?.value || currency).toUpperCase();
            const extendedNode = line.querySelector("[data-line-extended]");
            if (Number.isFinite(quantity) && Number.isFinite(price)) {
                const extended = quantity * price;
                priced += 1;
                total += extended;
                if (lineCurrency !== currency) mixed = true;
                if (extendedNode) {
                    try {
                        extendedNode.textContent = new Intl.NumberFormat(undefined, {
                            style: "currency",
                            currency: lineCurrency,
                            maximumFractionDigits: 2
                        }).format(extended);
                    } catch {
                        extendedNode.textContent = `${lineCurrency} ${extended.toFixed(2)}`;
                    }
                }
            } else if (extendedNode) {
                extendedNode.textContent = "—";
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
        const part = field(line, "part");
        const partSearch = field(line, "part_search");
        const partResults = line.querySelector("[data-part-results]");
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

        function hidePartResults() {
            if (partResults) {
                partResults.replaceChildren();
                partResults.hidden = true;
            }
        }

        function choosePart(selected) {
            if (!part || !partSearch || !selected) return;
            part.value = String(selected.pk);
            partSearch.value = selected.label || selected.IPN || selected.name || "";
            if (selected) {
                if (!description.value || description.dataset.partFilled === "true") {
                    description.value = selected.description || selected.name || "";
                    description.dataset.partFilled = "true";
                }
                if (!partNumber.value || partNumber.dataset.partFilled === "true") {
                    partNumber.value = selected.IPN || "";
                    partNumber.dataset.partFilled = "true";
                }
            }
            hidePartResults();
            dirty = true;
            scheduleResolve(true);
        }

        async function findParts(query) {
            if (!partSearchApi || !partResults || query.length < 2) {
                hidePartResults();
                return;
            }
            if (line.partSearchAbort) line.partSearchAbort.abort();
            line.partSearchAbort = new AbortController();
            try {
                const response = await fetch(
                    `${partSearchApi}?${new URLSearchParams({ q: query })}`,
                    {
                        credentials: "same-origin",
                        signal: line.partSearchAbort.signal,
                        headers: { Accept: "application/json" }
                    }
                );
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error("Part search is unavailable.");
                partResults.replaceChildren();
                (payload.results || []).forEach((result) => {
                    const option = document.createElement("button");
                    option.type = "button";
                    option.className = "part-result";
                    option.setAttribute("role", "option");
                    option.textContent = result.label || result.IPN || result.name;
                    option.addEventListener("click", () => choosePart(result));
                    partResults.appendChild(option);
                });
                partResults.hidden = !partResults.childElementCount;
            } catch (error) {
                if (error.name !== "AbortError") hidePartResults();
            }
        }

        let searchTimer;
        partSearch?.addEventListener("input", () => {
            if (part) part.value = "";
            window.clearTimeout(searchTimer);
            const query = partSearch.value.trim();
            searchTimer = window.setTimeout(() => findParts(query), 170);
            dirty = true;
            scheduleResolve(false);
        });
        partSearch?.addEventListener("keydown", (event) => {
            if (event.key === "Escape") hidePartResults();
        });
        partSearch?.addEventListener("blur", () => {
            window.setTimeout(hidePartResults, 150);
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
            partSearch?.focus();
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
    form.addEventListener("submit", (event) => {
        if (submitting) {
            event.preventDefault();
            return;
        }
        submitting = true;
        window.setTimeout(() => {
            form.querySelectorAll('button[type="submit"]').forEach((button) => {
                button.disabled = true;
            });
        }, 0);
    });
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
    page.querySelector("[data-sage-export]")?.addEventListener("click", (event) => {
        if (dirty && !window.confirm("Unsaved changes are not included in the Sage file. Download the last saved version anyway?")) {
            event.preventDefault();
        }
    });
    const firstError = page.querySelector(".field-error, .error-banner");
    if (firstError) firstError.scrollIntoView({ behavior: "smooth", block: "center" });
}

const editor = document.querySelector("[data-quote-editor-page]");
if (editor) initializeQuoteEditor(editor);
