from typing import Protocol, List, Dict, Any


class ExportRenderer(Protocol):
    async def render_excel(
        self,
        boq_data: Dict[str, Any],
        line_items_data: List[Dict[str, Any]],
        audit_events: List[Dict[str, Any]],
    ) -> bytes:
        """Renders submission-ready priced BoQ Excel workbook with audit sheet."""
        ...

    async def render_pdf(
        self,
        boq_data: Dict[str, Any],
        line_items_data: List[Dict[str, Any]],
        audit_events: List[Dict[str, Any]],
    ) -> bytes:
        """Renders submission-ready priced BoQ PDF document with quote references."""
        ...
