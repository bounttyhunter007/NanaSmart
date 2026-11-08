import os
from abc import ABC, abstractmethod

from google import genai
from google.genai import types


class AssistenteAdapter(ABC):
    """Contrato da aplicação para provedores de geração de conteúdo."""

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_content(
        self,
        system_instruction,
        user_prompt,
        history=None,
        model_candidates=None,
        temperature=0.4,
    ) -> tuple[str, str]:
        raise NotImplementedError


class GeminiAdapter(AssistenteAdapter):
    """Adapta o contrato da aplicação à API do SDK Google Gemini."""

    def get_client(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or not api_key.strip() or api_key == "CHAVEAQKUI":
            return None

        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None

    def is_available(self) -> bool:
        return self.get_client() is not None

    def generate_content(
        self,
        system_instruction,
        user_prompt,
        history=None,
        model_candidates=None,
        temperature=0.4,
    ) -> tuple[str, str]:
        client = self.get_client()
        if not client:
            raise RuntimeError("A chave GEMINI_API_KEY não está configurada ou é inválida.")

        if model_candidates is None:
            model_candidates = [
                "gemini-3.5-flash",
                "gemini-2.5-flash",
                "gemini-flash-latest",
            ]

        contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=item.get("text", ""))],
                    )
                )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            )
        )

        last_error = None
        for model_name in model_candidates:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                return response.text, model_name
            except Exception as error:
                error_text = str(error)
                recoverable = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "ResourceExhausted" in error_text
                    or "429" in error_text
                    or "404" in error_text
                    or "NOT_FOUND" in error_text
                    or "not found" in error_text.lower()
                )
                last_error = error
                if recoverable:
                    continue
                raise

        raise RuntimeError(f"Todos os modelos falharam. Erro: {last_error}")


def get_ai_adapter() -> AssistenteAdapter:
    """Ponto de composição: views dependem do contrato, não do SDK."""
    return GeminiAdapter()
