# Sales workflow roadmap

This remains one InvenTree plugin with clear internal boundaries. Sage-specific code stays
in the Windows Sage Bridge so the InvenTree server never needs the Sage SDK.

## 1. Quote foundation

- Finish and harden the current quote editor, pricing, PDFs, and tests.
- Keep quote wording and prices as snapshots for historical accuracy.

## 2. Accepted quote to Sage (implemented in 0.3.0)

- Keep the accepted quote as the source of truth instead of creating a native InvenTree
  Sales Order.
- Download one Sage Bridge CSV containing every quote line and accounting field.
- Use a stable invoice/order number so Sage Bridge can reject duplicate imports safely.

## 3. Fulfilment and packing slip

- Generate a branded packing slip directly from the accepted quote.
- Add an explicit stock-issue action for the parts Dad actually ships.
- Keep stock handling separate from the Sage accounting handoff.

## 4. Accounting handoff

- Record confirmation from Sage Bridge after an import succeeds.
- Display imported, skipped, and failed states on the quote page.
- Preserve an audit trail without treating a downloaded file as a completed import.

## 5. Sage Bridge integration

- Add an optional authenticated callback so the Windows Bridge can return its result.
- Continue supporting manual CSV downloads as a reliable fallback.

## Boundary

The quote plugin owns quoting, packing-slip data, and the approved accounting payload.
The Bridge owns all Sage SDK access. The official invoice comes from Sage; the branded
packing slip comes from the accepted quote in InvenTree.
