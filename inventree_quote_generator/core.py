"""InvenTree plugin entry point for customer-priced quote generation."""

from django.utils.translation import gettext_lazy as _
from plugin import InvenTreePlugin
from plugin.mixins import AppMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin

from . import PLUGIN_VERSION


class QuoteGeneratorPlugin(
    AppMixin,
    SettingsMixin,
    UrlsMixin,
    UserInterfaceMixin,
    InvenTreePlugin,
):
    """Create flexible, multi-line customer quotes from parts and pricing rules."""

    TITLE = "Quote Generator"
    NAME = "QuoteGeneratorPlugin"
    SLUG = "quote-generator"
    DESCRIPTION = "Generate polished multi-line quotes using customer quantity pricing."
    VERSION = PLUGIN_VERSION
    AUTHOR = "Matt Dick"
    LICENSE = "MIT"
    MIN_VERSION = "1.3.2"
    MAX_VERSION = "1.3.99"

    SETTINGS = {
        "COMPANY_NAME": {
            "name": _("Company name"),
            "description": _("Name shown in the quote letterhead."),
            "default": "DI-COR Engineering",
        },
        "COMPANY_ADDRESS": {
            "name": _("Company address"),
            "description": _("Single address line shown below the company name."),
            "default": "33 ROSELAND DRIVE, CARRYING PLACE, ONTARIO, CANADA K0K1L0",
        },
        "COMPANY_PHONE": {
            "name": _("Company phone"),
            "description": _("Phone line shown in the quote letterhead."),
            "default": "PHONE: (613) 392-7302",
        },
        "DEFAULT_CURRENCY": {
            "name": _("Default quote currency"),
            "description": _("Three-letter currency code used for new quotes."),
            "default": "CAD",
        },
        "DEFAULT_VALID_DAYS": {
            "name": _("Default validity in days"),
            "description": _("Used to prefill the valid-until date on new quotes."),
            "default": 30,
            "validator": int,
        },
        "INTRO_TEXT": {
            "name": _("Default introduction"),
            "description": _("Opening sentence for new quote PDFs."),
            "default": (
                "Regarding your recent request, we are pleased to offer the following "
                "for your consideration:"
            ),
        },
        "CURRENCY_TERMS": {
            "name": _("Default currency terms"),
            "description": _("First line in the Terms section."),
            "default": "All prices in CDN. Dollars.",
        },
        "AVAILABILITY_TERMS": {
            "name": _("Default availability terms"),
            "description": _("Text printed after the Availability label."),
            "default": "Stock from Receipt of Firm Purchase Order.",
        },
        "VALIDITY_TERMS": {
            "name": _("Default validity terms"),
            "description": _("Validity line shown in the Terms section."),
            "default": "Estimate Valid For 30 Days.",
        },
        "SALE_TERMS": {
            "name": _("Default sale terms"),
            "description": _("Final line in the Terms section."),
            "default": "Please see Terms of Sale.",
        },
        "CLOSING_TEXT": {
            "name": _("Default closing paragraph"),
            "description": _("Closing paragraph shown above tax and shipping notes."),
            "default": (
                "Thank you for allowing DI COR ENGINEERING, Inc. to be of service to you. "
                "If you require any additional information or if we can be of any further "
                "assistance, please feel free to contact us at (613) 399-2147. We look "
                "forward to hearing from you and serving your future food processing parts, "
                "equipment and service needs."
            ),
        },
        "TAX_NOTE": {
            "name": _("Default tax note"),
            "description": _("Tax note shown near the bottom of the quote."),
            "default": "Taxes extra. Prices in CDN funds.",
        },
        "FOB_NOTE": {
            "name": _("Default F.O.B. note"),
            "description": _("Shipping or delivery note shown near the bottom."),
            "default": "F.O.B. Customer Plant, Ontario",
        },
        "SIGNATORY_NAME": {
            "name": _("Default signatory"),
            "description": _("Name printed below Regards."),
            "default": "BRAD DICK",
        },
        "SIGNATORY_TITLE": {
            "name": _("Default signatory title"),
            "description": _("Optional title printed below the signatory name."),
            "default": "",
        },
    }

    @property
    def control_panel_url(self) -> str:
        return f"/{self.base_url.lstrip('/')}"

    @property
    def ui_script_url(self) -> str:
        return f"{self.control_panel_url}assets/ui.js?v={self.VERSION}"

    def ui_source(self, function_name: str) -> str:
        return f"{self.control_panel_url}assets/ui.js:{function_name}?v={self.VERSION}"

    def setup_urls(self):
        """Expose the quote workspace, actions, PDF downloads, and pricing API."""

        from django.urls import path
        from InvenTree.permissions import auth_exempt

        return [
            path("assets/<str:filename>", auth_exempt(self.asset_view), name="asset"),
            path("api/summary/", self.summary_api_view, name="summary-api"),
            path("api/resolve-price/", self.resolve_price_api_view, name="resolve-price-api"),
            path(
                "api/part/<int:part_id>/recent/",
                self.part_recent_quotes_api_view,
                name="part-recent-api",
            ),
            path("new/", self.quote_editor_view, name="quote-create"),
            path("<int:quote_id>/edit/", self.quote_editor_view, name="quote-edit"),
            path("<int:quote_id>/pdf/", self.quote_pdf_view, name="quote-pdf"),
            path("<int:quote_id>/duplicate/", self.quote_duplicate_view, name="quote-duplicate"),
            path("<int:quote_id>/delete/", self.quote_delete_view, name="quote-delete"),
            path("", self.quote_list_view, name="quote-list"),
        ]

    def asset_view(self, request, filename: str):
        from .views import package_asset

        return package_asset(request, filename)

    def quote_list_view(self, request):
        from .views import quote_list

        return quote_list(request, self)

    def quote_editor_view(self, request, quote_id: int | None = None):
        from .views import quote_editor

        return quote_editor(request, self, quote_id)

    def quote_pdf_view(self, request, quote_id: int):
        from .views import quote_pdf

        return quote_pdf(request, self, quote_id)

    def quote_duplicate_view(self, request, quote_id: int):
        from .views import duplicate_quote

        return duplicate_quote(request, self, quote_id)

    def quote_delete_view(self, request, quote_id: int):
        from .views import delete_quote

        return delete_quote(request, self, quote_id)

    def summary_api_view(self, request):
        from .views import quote_summary_api

        return quote_summary_api(request)

    def resolve_price_api_view(self, request):
        from .views import resolve_price_api

        return resolve_price_api(request)

    def part_recent_quotes_api_view(self, request, part_id: int):
        from .views import part_recent_quotes_api

        return part_recent_quotes_api(request, self, part_id)

    def get_ui_navigation_items(self, request, context, **kwargs):
        """Add a direct navigation entry to the separate quote workspace."""

        del context, kwargs
        from users.permissions import check_user_role

        if not request.user or not (
            request.user.is_superuser or check_user_role(request.user, "sales_order", "view")
        ):
            return []
        return [
            {
                "key": "quote-generator-workspace",
                "title": _("Quotes"),
                "description": _("Create and manage customer quotes"),
                "icon": "ti:file-invoice",
                "options": {"url": self.control_panel_url},
            }
        ]

    def get_ui_spotlight_actions(self, request, context, **kwargs):
        del context, kwargs
        from users.permissions import check_user_role

        if not request.user or not (
            request.user.is_superuser or check_user_role(request.user, "sales_order", "view")
        ):
            return []
        return [
            {
                "key": "open-quote-generator",
                "title": _("Quote Generator"),
                "description": _("Create or manage a customer quote"),
                "icon": "ti:file-invoice",
                "source": self.ui_source("openQuoteWorkspace"),
            }
        ]

    def get_ui_dashboard_items(self, request, context, **kwargs):
        del context, kwargs
        from users.permissions import check_user_role

        if not request.user or not (
            request.user.is_superuser or check_user_role(request.user, "sales_order", "view")
        ):
            return []
        return [
            {
                "key": "quote-generator-shortcut",
                "title": _("Quote Generator"),
                "description": _("Start a quote or continue a draft"),
                "source": self.ui_source("renderQuoteShortcut"),
                "options": {"width": 3, "height": 2},
                "context": {
                    "workspace_url": self.control_panel_url,
                    "create_url": f"{self.control_panel_url}new/",
                    "summary_url": f"{self.control_panel_url}api/summary/",
                },
            }
        ]

    def get_ui_panels(self, request, context: dict, **kwargs):
        """Place a quote action and recent quote list on every accessible part."""

        del kwargs
        if context.get("target_model") != "part":
            return []

        from part.models import Part
        from users.permissions import check_user_role

        if not request.user or not (
            request.user.is_superuser or check_user_role(request.user, "sales_order", "view")
        ):
            return []
        try:
            part = Part.objects.get(pk=context.get("target_id"))
        except (Part.DoesNotExist, TypeError, ValueError):
            return []

        return [
            {
                "key": "part-quote-generator",
                "title": _("Quotes"),
                "description": _("Create a customer quote using this part"),
                "icon": "ti:file-invoice",
                "source": self.ui_source("renderPartQuotePanel"),
                "context": {
                    "part_id": part.pk,
                    "part_name": part.name,
                    "part_ipn": part.IPN,
                    "create_url": f"{self.control_panel_url}new/?part_id={part.pk}",
                    "recent_url": f"{self.control_panel_url}api/part/{part.pk}/recent/",
                    "workspace_url": self.control_panel_url,
                },
            }
        ]
