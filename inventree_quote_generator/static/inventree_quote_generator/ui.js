const WORKSPACE_URL = "/plugin/quote-generator/";

function pluginData(context) {
    return context?.context || context || {};
}

function styleButton(link, primary = true) {
    Object.assign(link.style, {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "40px",
        padding: "0.5rem 0.9rem",
        borderRadius: "0.42rem",
        background: primary ? "#1971c2" : "#e9ecef",
        color: primary ? "#fff" : "#243746",
        fontSize: "0.875rem",
        fontWeight: "700",
        lineHeight: "1.2",
        textAlign: "center",
        textDecoration: "none"
    });
}

export function openQuoteWorkspace() {
    window.location.assign(WORKSPACE_URL);
}

export function renderQuoteShortcut(target, context) {
    if (!target) return;
    const data = pluginData(context);
    const workspaceUrl = data.workspace_url || WORKSPACE_URL;
    const createUrl = data.create_url || `${WORKSPACE_URL}new/`;
    const summaryUrl = data.summary_url || `${WORKSPACE_URL}api/summary/`;

    const shell = document.createElement("div");
    Object.assign(shell.style, {
        display: "grid",
        gridTemplateRows: "1fr auto",
        gap: "0.65rem",
        width: "100%",
        height: "100%",
        padding: "0.25rem"
    });
    const summary = document.createElement("a");
    summary.href = workspaceUrl;
    summary.textContent = "Open quote workspace";
    Object.assign(summary.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "54px",
        borderRadius: "0.45rem",
        color: "#24455b",
        background: "#edf4f7",
        fontWeight: "750",
        textDecoration: "none",
        textAlign: "center"
    });
    const create = document.createElement("a");
    create.href = createUrl;
    create.textContent = "Create a quote";
    styleButton(create, true);
    shell.append(summary, create);
    target.innerHTML = "";
    target.style.height = "100%";
    target.appendChild(shell);

    fetch(summaryUrl, { credentials: "same-origin", headers: { Accept: "application/json" } })
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((counts) => {
            summary.textContent = `${counts.drafts || 0} drafts · ${counts.awaiting || 0} open · ${counts.total || 0} total`;
        })
        .catch(() => {});
}

export function renderPartQuotePanel(target, context) {
    if (!target) return;
    const data = pluginData(context);
    const shell = document.createElement("div");
    Object.assign(shell.style, { display: "grid", gap: "0.9rem", padding: "0.3rem 0" });

    const heading = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = data.part_name || "This part";
    const detail = document.createElement("div");
    detail.textContent = data.part_ipn ? `IPN ${data.part_ipn}` : "Add this part to a customer quote.";
    Object.assign(detail.style, { marginTop: "0.2rem", color: "#687985", fontSize: "0.8rem" });
    heading.append(title, detail);

    const actions = document.createElement("div");
    Object.assign(actions.style, { display: "flex", flexWrap: "wrap", gap: "0.55rem" });
    const create = document.createElement("a");
    create.href = data.create_url || `${WORKSPACE_URL}new/?part_id=${data.part_id || ""}`;
    create.textContent = "Start quote with this part";
    styleButton(create, true);
    const all = document.createElement("a");
    all.href = data.workspace_url || WORKSPACE_URL;
    all.textContent = "All quotes";
    styleButton(all, false);
    actions.append(create, all);

    const recent = document.createElement("div");
    recent.textContent = "Checking recent quotes…";
    Object.assign(recent.style, { color: "#687985", fontSize: "0.82rem" });
    shell.append(heading, actions, recent);
    target.innerHTML = "";
    target.appendChild(shell);

    if (!data.recent_url) return;
    fetch(data.recent_url, { credentials: "same-origin", headers: { Accept: "application/json" } })
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((payload) => {
            recent.innerHTML = "";
            if (!payload.quotes?.length) {
                recent.textContent = "This part has not appeared on a saved quote yet.";
                return;
            }
            const label = document.createElement("div");
            label.textContent = "Recent quotes with this part";
            Object.assign(label.style, { marginBottom: "0.35rem", color: "#354f60", fontWeight: "750" });
            recent.appendChild(label);
            payload.quotes.forEach((quote) => {
                const link = document.createElement("a");
                link.href = quote.url;
                link.textContent = `${quote.number} · ${quote.customer} · ${quote.status}`;
                Object.assign(link.style, { display: "block", padding: "0.25rem 0", color: "#1971c2", textDecoration: "none" });
                recent.appendChild(link);
            });
        })
        .catch(() => { recent.textContent = "Recent quotes could not be loaded."; });
}
