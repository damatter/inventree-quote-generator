"""Enable the plugin in the disposable official-container test database."""

from common.models import InvenTreeSetting
from django.utils.text import slugify
from plugin.models import PluginConfig
from plugin.registry import registry

for key in ("ENABLE_PLUGINS_APP", "ENABLE_PLUGINS_URL", "ENABLE_PLUGINS_INTERFACE"):
    InvenTreeSetting.set_setting(key, True)
for plugin in registry.collect_plugins():
    slug = slugify(getattr(plugin, "SLUG", None) or plugin.NAME)
    config = PluginConfig.objects.filter(key=slug).first() or PluginConfig(key=slug)
    config.name = plugin.NAME
    if slug == "quote-generator":
        config.active = True
    config.save(no_reload=True)

registry.reload_plugins(collect=True, force_reload=True, full_reload=True)
assert registry.get_plugin("quote-generator", active=True), registry.errors
