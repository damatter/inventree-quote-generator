# Sales workflow roadmap

This remains one InvenTree plugin with clear internal boundaries. Sage-specific code stays
in the Windows Sage Bridge so the InvenTree server never needs the Sage SDK.

## 1. Quote foundation

- Finish and harden the current quote editor, pricing, PDFs, and tests.
- Keep quote wording and prices as snapshots for historical accuracy.

## 2. Accepted quote to sales order

- Convert an accepted quote once into a pending native InvenTree Sales Order.
- Preserve part, quantity, description, price, currency, and quote traceability.
- Let Dad review and issue the native order before stock allocation begins.

## 3. Fulfilment and packing slip

- Use native Sales Order shipments, including partial shipments.
- Configure a branded shipment report as the packing slip / customer PDF.
- Record ship date and the Sales Order reference (the current “job code”).

## 4. Accounting handoff

- Mark each completed shipment Ready for Accounting.
- Expose a stable, idempotent payload containing customer, dates, quantities,
  descriptions, prices, tax code, and Sales Order reference.
- Record pending, exported, and failed states so nothing is silently duplicated or lost.

## 5. Sage Bridge integration

- Have the Windows Bridge fetch only approved shipment payloads.
- Create the Sage invoice and write the Sage invoice number back to InvenTree.
- Support retries without creating duplicate invoices.

## Boundary

The plugin owns the workflow inside InvenTree. The Bridge owns all Sage SDK access. The
official invoice comes from Sage; the branded packing slip comes from InvenTree.
