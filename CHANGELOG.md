# Changelog

## 0.3.0 - 2026-09-22

- Replace native InvenTree Sales Order creation with a direct accepted-quote Sage handoff.
- Export every quote line in one Sage Bridge CSV.
- Add editable Sage customer, transaction type, number, invoice/order date, ship date,
  revenue account, and HST/tax code fields.
- Track how many times a Sage file was prepared and when it was last downloaded.
- Preserve legacy native Sales Order links without using them for new quotes.
- Update duplicate-quote handling so legacy links and Sage export history are never copied.

## 0.2.1 - 2026-09-22

- Move new-quote defaults to the main quote workspace.
- Add status changes and accepted-quote Sales Order creation to the quote list.
- Open saved PDF previews in a new browser tab.
- Prevent a reused new-quote form from creating a duplicate quote.
- Remove the incompatible top navigation shortcut.

## 0.2.0 - 2026-09-22

- Add duplicate-safe conversion from an accepted quote to a pending native InvenTree
  Sales Order.
- Preserve quote quantities, price snapshots, currency, part references, and custom lines.
- Add a type-ahead part search to replace the full part dropdown.
- Fix reusable defaults not appearing on new quotes.
- Add a staged roadmap for packing slips and the Sage accounting handoff.

## 0.1.1 - 2026-09-01

- Add editable quote defaults and letterhead snapshots.
- Improve plugin startup and browser asset delivery.
