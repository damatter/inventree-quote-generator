# InvenTree Quote Generator

An InvenTree 1.3.x plugin for creating polished, multi-line customer quote PDFs and sending
accepted quotes directly to the Sage 50 Canada Bridge.

The PDF layout follows the supplied DI-COR quote: logo and letterhead, date, customer,
subject, optional manufacturer/item/model details, compact quoted lines, Terms section,
closing paragraph, tax/F.O.B. notes, and signatory.

## What it adds

- A **Quotes** panel on every accessible part page with **Start quote with this part**.
- A **Quote Generator** dashboard widget with a one-click create button and live counts.
- A spotlight shortcut to a separate quote workspace.
- A responsive quote site for searching, creating, editing, duplicating, previewing,
  downloading, and deleting quotes.
- Any number of line items per quote, including custom lines with no InvenTree part.
- A fast, type-ahead InvenTree part search instead of a full-part dropdown.
- A sample-style DI-COR preset automatically applied to every new quote, with editable
  per-quote fields and workspace defaults.
- Clearly labeled price-each and calculated extended-price values for every line.
- Automatic customer- and quantity-specific pricing from `inventree-customer-pricing`.
- A visible manual-price fallback when the selected customer/part/quantity has no rule.
- Optional blank prices and optional blank presentation fields.
- Draft/ready/sent/accepted/declined/expired workflow statuses.
- Status changes and Sage exports directly from the quote list.
- One Sage Bridge CSV per accepted quote, containing every line item plus the customer,
  transaction number, invoice/order date, ship date, revenue account, and tax code.
- Stable transaction numbers so repeated downloads are safely skipped by Sage Bridge
  instead of creating duplicate invoices.
- PDF preview, stable PDF filenames, quote numbering, validity dates, internal notes,
  per-line availability/notes, and an optional same-currency subtotal.

## Compatibility

- InvenTree `1.3.2` through `1.3.x`
- Python `3.11` or newer, including Python `3.14`
- The React-based InvenTree user interface
- `inventree-customer-pricing` `0.6.1` for automatic customer price resolution

The quote plugin still works when Customer Pricing is missing or inactive. In that case,
every line switches to manual pricing and explains why.

## Install

[Latest release](https://github.com/damatter/inventree-quote-generator/releases/latest) ·
[Version 0.3.0](https://github.com/damatter/inventree-quote-generator/releases/tag/0.3.0) ·
[Changelog](https://github.com/damatter/inventree-quote-generator/blob/0.3.0/CHANGELOG.md)

In **Admin Center → Plugins → Install Plugin**, enter these values exactly:

```text
Package Name: inventree-quote-generator
Source URL:  git+https://github.com/damatter/inventree-quote-generator.git@0.3.0
Version:     (leave blank)
```

Then:

1. Enable custom plugins, plugin apps, plugin URL integrations, and plugin UI integrations.
2. Restart the InvenTree web server and background worker.
3. Activate **Quote Generator** in Admin Center.
4. Run the normal InvenTree update/migration step, then restart once more.
5. Add the **Quote Generator** widget from the dashboard widget library if it is not already
   on the dashboard.

Container installations should enable **Check Plugins on Startup** so the installed plugin
is restored after container replacement.

### Update an existing installation to 0.3.0

Return to **Admin Center → Plugins** and edit or reinstall the package using the same values,
changing only the release tag at the end of **Source URL**:

```text
Package Name: inventree-quote-generator
Source URL:  git+https://github.com/damatter/inventree-quote-generator.git@0.3.0
Version:     (leave blank)
```

Confirm the installation, run the normal InvenTree update/migration step, and restart both
the web server and background worker. Do not also enter a value in **Version** when the
version is already pinned in **Source URL**.

On InvenTree 1.3.x, stop the background worker before installing or updating a plugin,
then start it after the migration and static-file step completes. This avoids the known
multi-process plugin static-file race.

For installations managed directly with `plugins.txt`, use:

```text
inventree-quote-generator @ git+https://github.com/damatter/inventree-quote-generator.git@0.3.0
```

Update by changing the tag after the final `@`, then run `invoke plugins` (or the normal
InvenTree update process) and restart the web server and worker.

## Pricing behavior

For an automatic line the plugin looks for an active Customer Pricing list matching both
the selected customer and part. It chooses the largest minimum-quantity break that is less
than or equal to the quote quantity and snapshots the resulting unit price, currency, and
source on the quote line.

If no list or applicable break exists, the editor switches that line to **Manual price**.
The manual price may be entered or intentionally left blank. Automatic prices are checked
again when the quote is saved, so quantity or customer changes cannot leave a stale rule.

The quote stores snapshots: later changes to the part name, IPN, customer, or pricing rules
do not silently rewrite already-saved wording or prices unless the quote is edited and saved.

## Configuration

Admin Center plugin settings contain the defaults used for new quotes:

- company name, address, and phone;
- currency and validity period;
- introduction, four Terms lines, closing paragraph, tax note, and F.O.B. note;
- signatory name and optional title.

Superusers can also edit every reusable default from the collapsible **Defaults for new
quotes** panel on the main quote workspace. Each saved quote snapshots its own company name,
letterhead address, and phone, so changing defaults does not rewrite older quotes.

Browser assets are served directly by the plugin rather than copied through Django's shared
static-file collection step. This avoids worker startup races in multi-process containers.

All of those values remain editable on each quote, and all except the selected customer can
be blank.

## Permissions

- Sales-order `view` can list and generate existing quote PDFs.
- Sales-order `change` can create, edit, duplicate, delete, and export quotes to Sage.
- Superusers retain full access.

## Development checks

```bash
python -m compileall inventree_quote_generator tests
python -m pytest
python -m build
```

## Quote-to-Sage workflow

1. Finish the quote and mark it **Accepted**.
2. In **Sage handoff**, confirm the exact Sage customer name, transaction type, dates,
   revenue account, and tax code, then save.
3. Click **Download Sage file** and open the CSV in Sage Bridge.
4. Review the lines and import them. Sage Bridge checks the transaction number before
   posting, so downloading or importing the same quote again does not create a duplicate.

This workflow intentionally does not create an InvenTree Sales Order. Historical links
created by versions 0.2.0 and 0.2.1 remain stored, but new quotes go directly to Sage.
The next planned step is a branded packing slip and an explicit stock-issue action; see
the [sales workflow roadmap](ROADMAP.md).
