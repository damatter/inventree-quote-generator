# InvenTree Quote Generator

An InvenTree 1.3.x plugin for creating polished, multi-line customer quote PDFs and moving
accepted quotes into the native InvenTree sales workflow.

The PDF layout follows the supplied DI-COR quote: logo and letterhead, date, customer,
subject, optional manufacturer/item/model details, compact quoted lines, Terms section,
closing paragraph, tax/F.O.B. notes, and signatory.

## What it adds

- A **Quotes** panel on every accessible part page with **Start quote with this part**.
- A **Quote Generator** dashboard widget with a one-click create button and live counts.
- A navigation and spotlight shortcut to a separate quote workspace.
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
- One-click, duplicate-safe conversion of an accepted quote into a pending native
  InvenTree Sales Order.
- PDF preview, stable PDF filenames, quote numbering, validity dates, internal notes,
  per-line availability/notes, and an optional same-currency subtotal.

## Compatibility

- InvenTree `1.3.2` through `1.3.x`
- Python `3.11` or newer, including Python `3.14`
- The React-based InvenTree user interface
- `inventree-customer-pricing` `0.2.0` for automatic customer price resolution

The quote plugin still works when Customer Pricing is missing or inactive. In that case,
every line switches to manual pricing and explains why.

## Install

[Latest release](https://github.com/damatter/inventree-quote-generator/releases/latest) ·
[Version 0.2.0](https://github.com/damatter/inventree-quote-generator/releases/tag/0.2.0) ·
[Changelog](https://github.com/damatter/inventree-quote-generator/blob/0.2.0/CHANGELOG.md)

In **Admin Center → Plugins → Install Plugin**, enter these values exactly:

```text
Package Name: inventree-quote-generator
Source URL:  git+https://github.com/damatter/inventree-quote-generator.git@0.2.0
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

### Update an existing installation to 0.2.0

Return to **Admin Center → Plugins** and edit or reinstall the package using the same values,
changing only the release tag at the end of **Source URL**:

```text
Package Name: inventree-quote-generator
Source URL:  git+https://github.com/damatter/inventree-quote-generator.git@0.2.0
Version:     (leave blank)
```

Confirm the installation, run the normal InvenTree update/migration step, and restart both
the web server and background worker. Do not also enter a value in **Version** when the
version is already pinned in **Source URL**.

For installations managed directly with `plugins.txt`, use:

```text
inventree-quote-generator @ git+https://github.com/damatter/inventree-quote-generator.git@0.2.0
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
quotes** panel on the quote editor. Each saved quote snapshots its own company name,
letterhead address, and phone, so changing defaults does not rewrite older quotes.

Browser assets are served directly by the plugin rather than copied through Django's shared
static-file collection step. This avoids worker startup races in multi-process containers.

All of those values remain editable on each quote, and all except the selected customer can
be blank.

## Permissions

- Sales-order `view` can list and generate existing quote PDFs.
- Sales-order `change` can create, edit, duplicate, and delete quotes.
- Superusers retain full access.

## Development checks

```bash
python -m compileall inventree_quote_generator tests
python -m pytest
python -m build
```

## Sales workflow

An accepted quote can create one pending native InvenTree Sales Order. The order is left
pending for review; the plugin does not automatically issue it, allocate stock, ship it, or
create a Sage invoice. See the [sales workflow roadmap](ROADMAP.md) for the planned branded
packing slip and accounting handoff stages.
