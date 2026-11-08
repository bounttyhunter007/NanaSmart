from .context_service import build_base_context, get_financial_summary


class GeminiContextFacade:
    """Oferece às views uma entrada única para montar o contexto da IA."""

    def build_context(self, user, *, include_financial_summary=False):
        context = build_base_context(user)
        if include_financial_summary:
            context["financial_summary"] = get_financial_summary(user)
        return context
