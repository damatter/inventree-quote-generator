"""Authenticated server-rendered quote workspace and small JSON endpoints."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

QUOTE_SUBMISSION_SESSION_KEY = "quote_generator_submissions"


def _has_sales_role(user, action: str) -> bool:
    from users.permissions import check_user_role

    return bool(user and (user.is_superuser or check_user_role(user, "sales_order", action)))


def _require_sales_role(user, action: str) -> None:
    from django.core.exceptions import PermissionDenied

    if not _has_sales_role(user, action):
        raise PermissionDenied(f"The sales_order.{action} role is required for quotes.")


def _positive_int(value) -> int | None:
    try:
        result = int(str(value))
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def package_asset(request, filename: str):
    """Serve the plugin's tiny browser assets without depending on collectstatic."""

    from django.http import Http404, HttpResponse

    del request
    content_types = {
        "ui.js": "text/javascript; charset=utf-8",
        "site.js": "text/javascript; charset=utf-8",
        "site.css": "text/css; charset=utf-8",
    }
    if filename not in content_types:
        raise Http404("Asset not found")
    asset_path = Path(__file__).parent / "assets" / filename
    if not asset_path.is_file():
        raise Http404("Asset not found")
    response = HttpResponse(
        asset_path.read_text(encoding="utf-8"),
        content_type=content_types[filename],
    )
    response["Cache-Control"] = "public, max-age=300"
    return response


def quote_list(request, plugin):
    """Show filterable quote history and workspace-level actions."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.core.paginator import Paginator
    from django.db.models import Count, Q
    from django.shortcuts import redirect, render

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        from .forms import QuoteDefaultsForm
        from .models import Quote

        can_manage_defaults = bool(request.user.is_superuser)
        saving_defaults = (
            request.method == "POST" and request.POST.get("form_action") == "save_defaults"
        )
        defaults_form = (
            QuoteDefaultsForm(
                request.POST if saving_defaults else None,
                plugin=plugin,
                prefix="defaults",
            )
            if can_manage_defaults
            else None
        )
        if request.method == "POST":
            if not saving_defaults:
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied("Unsupported quote workspace action.")
            if not can_manage_defaults:
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied("Only superusers can change quote defaults.")
            if defaults_form.is_valid():
                defaults_form.save(user=request.user)
                messages.success(request, "Defaults for new quotes were saved.")
                return redirect(plugin.control_panel_url)

        query = str(request.GET.get("q", "") or "").strip()[:200]
        status_filter = str(request.GET.get("status", "") or "")
        if status_filter not in Quote.Status.values:
            status_filter = ""

        quotes = Quote.objects.select_related("customer", "updated_by").annotate(
            line_count=Count("line_items")
        )
        if query:
            quotes = quotes.filter(
                Q(quote_number__icontains=query)
                | Q(customer_name__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(subject__icontains=query)
                | Q(line_items__part_number__icontains=query)
                | Q(line_items__description__icontains=query)
            ).distinct()
        if status_filter:
            quotes = quotes.filter(status=status_filter)

        page_obj = Paginator(quotes, 30).get_page(_positive_int(request.GET.get("page")) or 1)
        sales_orders = {}
        sales_order_ids = [
            quote.sales_order_id for quote in page_obj.object_list if quote.sales_order_id
        ]
        if sales_order_ids:
            from order.models import SalesOrder

            sales_orders = SalesOrder.objects.in_bulk(sales_order_ids)
        for quote in page_obj.object_list:
            quote.linked_sales_order = sales_orders.get(quote.sales_order_id)
            quote.sales_order_url = (
                quote.linked_sales_order.get_absolute_url() if quote.linked_sales_order else ""
            )
        totals = Quote.objects.aggregate(
            total=Count("pk"),
            drafts=Count("pk", filter=Q(status=Quote.Status.DRAFT)),
            active=Count("pk", filter=Q(status__in=[Quote.Status.READY, Quote.Status.SENT])),
        )
        context = {
            "plugin_title": plugin.TITLE,
            "plugin_version": plugin.VERSION,
            "control_panel_url": plugin.control_panel_url,
            "create_url": f"{plugin.control_panel_url}new/",
            "site_css_url": f"{plugin.control_panel_url}assets/site.css?v={plugin.VERSION}",
            "site_js_url": f"{plugin.control_panel_url}assets/site.js?v={plugin.VERSION}",
            "quotes": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "status_choices": Quote.Status.choices,
            "totals": totals,
            "can_change": _has_sales_role(request.user, "change"),
            "can_manage_defaults": can_manage_defaults,
            "defaults_form": defaults_form,
        }
        response = render(request, "inventree_quote_generator/quote_list.html", context)
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def _requested_customer(post_data):
    from company.models import Company

    customer_id = _positive_int(post_data.get("customer"))
    if customer_id is None:
        return None
    return Company.objects.filter(pk=customer_id, is_customer=True).first()


def _line_initial(part):
    if part is None:
        return None
    return {
        "part": part,
        "quantity": Decimal("1"),
        "unit": "pcs.",
        "description": part.name,
        "part_number": part.IPN,
        "price_mode": "auto",
    }


def quote_editor(request, plugin, quote_id: int | None = None):
    """Create or edit one quote and any number of dynamic line items."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.db import transaction
    from django.http import Http404
    from django.shortcuts import redirect, render
    from part.models import Part

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "change")
        from .forms import QuoteForm, QuoteLineItemFormSet
        from .models import Quote

        if quote_id is None:
            quote = Quote()
        else:
            try:
                quote = Quote.objects.select_related("customer").get(pk=quote_id)
            except Quote.DoesNotExist as error:
                raise Http404("Quote not found") from error

        initial_part = None
        if quote_id is None:
            part_id = _positive_int(request.GET.get("part_id"))
            if part_id is not None:
                initial_part = Part.objects.filter(pk=part_id, active=True).first()

        submission_token = str(request.POST.get("submission_token", "") or "")
        if quote_id is None and request.method == "POST" and submission_token:
            submissions = request.session.get(QUOTE_SUBMISSION_SESSION_KEY, {})
            saved_quote_id = _positive_int(submissions.get(submission_token))
            if saved_quote_id and Quote.objects.filter(pk=saved_quote_id).exists():
                messages.info(
                    request,
                    "That new quote was already saved. You are viewing the existing quote.",
                )
                return redirect(f"{plugin.control_panel_url}{saved_quote_id}/edit/")

        if request.method == "POST":
            quote_form = QuoteForm(request.POST, instance=quote, plugin=plugin)
            customer = _requested_customer(request.POST)
            posted_currency = str(request.POST.get("currency", "CAD") or "CAD")

            if quote_form.is_valid():
                pending_quote = quote_form.save(commit=False)
                customer = quote_form.cleaned_data["customer"]
                posted_currency = quote_form.cleaned_data["currency"]
                line_formset = QuoteLineItemFormSet(
                    request.POST,
                    instance=pending_quote,
                    prefix="lines",
                    form_kwargs={"customer": customer, "quote_currency": posted_currency},
                )
                if line_formset.is_valid():
                    with transaction.atomic():
                        previous_customer_id = quote.customer_id if quote.pk else None
                        saved_quote = quote_form.save(commit=False)
                        if not saved_quote.pk:
                            saved_quote.created_by = request.user
                        saved_quote.updated_by = request.user
                        if previous_customer_id != saved_quote.customer_id:
                            saved_quote.customer_name = saved_quote.customer.name
                        saved_quote.save()

                        for line_form in line_formset.forms:
                            data = getattr(line_form, "cleaned_data", {})
                            instance = line_form.instance
                            if data.get("DELETE"):
                                if instance.pk:
                                    instance.delete()
                                continue
                            if not (
                                data.get("part")
                                or data.get("description")
                                or data.get("part_number")
                            ):
                                continue
                            line = line_form.save(commit=False)
                            line.quote = saved_quote
                            position = line_formset.forms.index(line_form)
                            line.sort_order = sum(
                                1
                                for earlier in line_formset.forms[:position]
                                if getattr(earlier, "cleaned_data", {}).get("DELETE") is not True
                            )
                            line.currency = (line.currency or saved_quote.currency).upper()
                            line.save()

                    messages.success(request, f"{saved_quote.quote_number} saved.")
                    if quote_id is None and submission_token:
                        submissions = request.session.get(QUOTE_SUBMISSION_SESSION_KEY, {})
                        submissions[submission_token] = saved_quote.pk
                        request.session[QUOTE_SUBMISSION_SESSION_KEY] = dict(
                            list(submissions.items())[-20:]
                        )
                    return redirect(f"{plugin.control_panel_url}{saved_quote.pk}/edit/?saved=1")
            else:
                line_formset = QuoteLineItemFormSet(
                    request.POST,
                    instance=quote,
                    prefix="lines",
                    form_kwargs={"customer": customer, "quote_currency": posted_currency},
                )
        else:
            submission_token = uuid4().hex if quote_id is None else ""
            quote_form = QuoteForm(instance=quote, plugin=plugin, initial_part=initial_part)
            initial = [_line_initial(initial_part)] if initial_part is not None else None
            line_formset = QuoteLineItemFormSet(
                instance=quote,
                prefix="lines",
                initial=initial,
                form_kwargs={
                    "customer": quote.customer if quote.pk else None,
                    "quote_currency": (
                        quote.currency if quote.pk else plugin.get_setting("DEFAULT_CURRENCY")
                    ),
                },
            )

        customers_catalog = list(
            quote_form.fields["customer"].queryset.values("pk", "name", "currency")
        )
        sales_order = None
        if quote.pk and quote.sales_order_id:
            from order.models import SalesOrder

            sales_order = SalesOrder.objects.filter(pk=quote.sales_order_id).first()
        context = {
            "plugin_title": plugin.TITLE,
            "plugin_version": plugin.VERSION,
            "control_panel_url": plugin.control_panel_url,
            "site_css_url": f"{plugin.control_panel_url}assets/site.css?v={plugin.VERSION}",
            "site_js_url": f"{plugin.control_panel_url}assets/site.js?v={plugin.VERSION}",
            "quote": quote,
            "quote_form": quote_form,
            "submission_token": submission_token,
            "line_formset": line_formset,
            "customers_catalog": customers_catalog,
            "price_api_url": f"{plugin.control_panel_url}api/resolve-price/",
            "part_search_api_url": f"{plugin.control_panel_url}api/parts/search/",
            "pdf_url": f"{plugin.control_panel_url}{quote.pk}/pdf/" if quote.pk else "",
            "duplicate_url": (
                f"{plugin.control_panel_url}{quote.pk}/duplicate/" if quote.pk else ""
            ),
            "delete_url": f"{plugin.control_panel_url}{quote.pk}/delete/" if quote.pk else "",
            "convert_url": (
                f"{plugin.control_panel_url}{quote.pk}/create-sales-order/" if quote.pk else ""
            ),
            "sales_order": sales_order,
            "sales_order_url": sales_order.get_absolute_url() if sales_order else "",
        }
        response = render(request, "inventree_quote_generator/quote_editor.html", context)
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def update_quote_status(request, plugin, quote_id: int):
    """Update a quote's workflow status from the main workspace."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.shortcuts import get_object_or_404, redirect
    from django.views.decorators.http import require_POST

    @login_required
    @require_POST
    def authenticated_view(request):
        _require_sales_role(request.user, "change")
        from .models import Quote

        quote = get_object_or_404(Quote, pk=quote_id)
        status = str(request.POST.get("status", "") or "")
        if status not in Quote.Status.values:
            messages.error(request, "Choose a valid quote status.")
            return redirect(plugin.control_panel_url)
        if quote.status != status:
            quote.status = status
            quote.updated_by = request.user
            quote.save(update_fields=["status", "updated_by", "updated"])
            messages.success(request, f"{quote.quote_number} status updated.")
        return redirect(plugin.control_panel_url)

    return authenticated_view(request)


def create_sales_order(request, plugin, quote_id: int):
    """Create a pending native InvenTree sales order from an accepted quote."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.core.exceptions import ValidationError
    from django.shortcuts import get_object_or_404, redirect
    from django.views.decorators.http import require_POST

    @login_required
    @require_POST
    def authenticated_view(request):
        _require_sales_role(request.user, "change")
        from .models import Quote
        from .workflow import convert_quote_to_sales_order

        quote = get_object_or_404(Quote, pk=quote_id)
        return_to_list = request.POST.get("return_to") == "list"
        requested_status = str(request.POST.get("status", "") or "")
        if requested_status:
            if requested_status not in Quote.Status.values:
                messages.error(request, "Choose a valid quote status.")
                return redirect(
                    plugin.control_panel_url
                    if return_to_list
                    else f"{plugin.control_panel_url}{quote.pk}/edit/"
                )
            if quote.status != requested_status:
                quote.status = requested_status
                quote.updated_by = request.user
                quote.save(update_fields=["status", "updated_by", "updated"])
        try:
            sales_order, created = convert_quote_to_sales_order(quote, request.user)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return redirect(
                plugin.control_panel_url
                if return_to_list
                else f"{plugin.control_panel_url}{quote.pk}/edit/"
            )

        if created:
            messages.success(
                request,
                f"Sales order {sales_order.reference} was created as a pending order.",
            )
        return redirect(sales_order.get_absolute_url())

    return authenticated_view(request)


def quote_pdf(request, plugin, quote_id: int):
    """Preview or download the current quote snapshot as a PDF."""

    from django.contrib.auth.decorators import login_required
    from django.db.models import F
    from django.http import Http404, HttpResponse
    from django.utils import timezone

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        from .models import Quote
        from .pdf import quote_document_from_model, quote_pdf_filename, render_quote_pdf

        try:
            quote = (
                Quote.objects.select_related("customer")
                .prefetch_related("line_items")
                .get(pk=quote_id)
            )
        except Quote.DoesNotExist as error:
            raise Http404("Quote not found") from error

        payload = render_quote_pdf(quote_document_from_model(quote, plugin))
        download = str(request.GET.get("download", "")).casefold() in {"1", "true", "yes"}
        if download:
            Quote.objects.filter(pk=quote.pk).update(
                last_generated_at=timezone.now(),
                generation_count=F("generation_count") + 1,
            )

        filename = quote_pdf_filename(quote.quote_number, quote.customer_name, quote.subject)
        response = HttpResponse(payload, content_type="application/pdf")
        disposition = "attachment" if download else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def duplicate_quote(request, plugin, quote_id: int):
    """Clone a quote into a fresh draft with a new number and current date."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.db import transaction
    from django.http import Http404
    from django.shortcuts import redirect
    from django.utils import timezone
    from django.views.decorators.http import require_POST

    @login_required
    @require_POST
    def authenticated_view(request):
        _require_sales_role(request.user, "change")
        from .models import Quote, QuoteLineItem

        try:
            source = Quote.objects.prefetch_related("line_items").get(pk=quote_id)
        except Quote.DoesNotExist as error:
            raise Http404("Quote not found") from error

        excluded = {
            "id",
            "quote_number",
            "status",
            "issue_date",
            "valid_until",
            "created_by",
            "updated_by",
            "created",
            "updated",
            "last_generated_at",
            "generation_count",
        }
        values = {
            field.name: getattr(source, field.name)
            for field in Quote._meta.fields
            if field.name not in excluded
        }
        today = timezone.localdate()
        validity_days = (
            (source.valid_until - source.issue_date).days
            if source.valid_until and source.issue_date
            else int(plugin.get_setting("DEFAULT_VALID_DAYS") or 30)
        )
        with transaction.atomic():
            clone = Quote.objects.create(
                **values,
                status=Quote.Status.DRAFT,
                issue_date=today,
                valid_until=today + timedelta(days=max(0, validity_days)),
                created_by=request.user,
                updated_by=request.user,
            )
            line_excluded = {"id", "quote", "created", "updated"}
            for item in source.line_items.all():
                line_values = {
                    field.name: getattr(item, field.name)
                    for field in QuoteLineItem._meta.fields
                    if field.name not in line_excluded
                }
                QuoteLineItem.objects.create(quote=clone, **line_values)

        messages.success(request, f"Created draft {clone.quote_number} from {source.quote_number}.")
        return redirect(f"{plugin.control_panel_url}{clone.pk}/edit/")

    return authenticated_view(request)


def delete_quote(request, plugin, quote_id: int):
    """Permanently remove one quote after an explicit editor confirmation."""

    from django.contrib import messages
    from django.contrib.auth.decorators import login_required
    from django.http import Http404
    from django.shortcuts import redirect
    from django.views.decorators.http import require_POST

    @login_required
    @require_POST
    def authenticated_view(request):
        _require_sales_role(request.user, "change")
        from .models import Quote

        try:
            quote = Quote.objects.get(pk=quote_id)
        except Quote.DoesNotExist as error:
            raise Http404("Quote not found") from error
        number = quote.quote_number
        quote.delete()
        messages.success(request, f"{number} was deleted.")
        return redirect(plugin.control_panel_url)

    return authenticated_view(request)


def quote_summary_api(request):
    """Return compact counts for the dashboard shortcut."""

    from django.contrib.auth.decorators import login_required
    from django.db.models import Count, Q
    from django.http import JsonResponse

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        from .models import Quote

        summary = Quote.objects.aggregate(
            total=Count("pk"),
            drafts=Count("pk", filter=Q(status=Quote.Status.DRAFT)),
            awaiting=Count("pk", filter=Q(status__in=[Quote.Status.READY, Quote.Status.SENT])),
        )
        response = JsonResponse(summary)
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def resolve_price_api(request):
    """Resolve a customer quantity price for an interactive line item."""

    from django.contrib.auth.decorators import login_required
    from django.http import JsonResponse

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        from .pricing import resolve_customer_price

        customer_id = _positive_int(request.GET.get("customer"))
        part_id = _positive_int(request.GET.get("part"))
        try:
            quantity = Decimal(str(request.GET.get("quantity", "")))
        except (InvalidOperation, TypeError, ValueError):
            quantity = None
        if customer_id is None or part_id is None or quantity is None or quantity < 0:
            return JsonResponse(
                {"found": False, "message": "Choose a customer, part, and valid quantity."},
                status=400,
            )
        result = resolve_customer_price(customer_id, part_id, quantity)
        response = JsonResponse(
            {
                "found": result.found,
                "unit_price": (
                    format(result.unit_price, "f") if result.unit_price is not None else None
                ),
                "currency": result.currency,
                "price_break_id": result.price_break_id,
                "source": result.source,
                "message": result.message,
            }
        )
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def part_search_api(request):
    """Return a small, searchable part catalog for the quote line picker."""

    from django.contrib.auth.decorators import login_required
    from django.db.models import Q
    from django.http import JsonResponse
    from part.models import Part

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        query = str(request.GET.get("q", "") or "").strip()
        if len(query) < 2:
            return JsonResponse({"results": []})

        parts = (
            Part.objects.filter(active=True)
            .filter(
                Q(IPN__icontains=query) | Q(name__icontains=query) | Q(description__icontains=query)
            )
            .order_by("IPN", "name")[:25]
        )
        results = [
            {
                "pk": part.pk,
                "IPN": part.IPN or "",
                "name": part.name or "",
                "description": part.description or "",
                "label": " - ".join(
                    value for value in (part.IPN, part.name or part.description) if value
                ),
            }
            for part in parts
        ]
        response = JsonResponse({"results": results})
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)


def part_recent_quotes_api(request, plugin, part_id: int):
    """List recent quotes containing a part for the part-detail panel."""

    from django.contrib.auth.decorators import login_required
    from django.http import JsonResponse

    @login_required
    def authenticated_view(request):
        _require_sales_role(request.user, "view")
        from .models import Quote

        records = (
            Quote.objects.filter(line_items__part_id=part_id)
            .distinct()
            .order_by("-issue_date", "-pk")[:5]
        )
        response = JsonResponse(
            {
                "quotes": [
                    {
                        "pk": quote.pk,
                        "number": quote.quote_number,
                        "customer": quote.customer_name,
                        "status": quote.get_status_display(),
                        "date": quote.issue_date.isoformat(),
                        "url": f"{plugin.control_panel_url}{quote.pk}/edit/",
                    }
                    for quote in records
                ]
            }
        )
        response["Cache-Control"] = "no-store"
        return response

    return authenticated_view(request)
