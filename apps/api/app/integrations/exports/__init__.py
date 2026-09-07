from app.integrations.exports.base import ExportRenderer
from app.integrations.exports.renderer import StandardExportRenderer

_export_renderer: ExportRenderer = None


def get_export_renderer() -> ExportRenderer:
    global _export_renderer
    if _export_renderer is None:
        _export_renderer = StandardExportRenderer()
    return _export_renderer
