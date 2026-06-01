# src/rag_course/infrastructure/llm/cohere_llm.py
import cohere

from rag_course.config.settings import settings
from rag_course.domain.ports import ILanguageModel


class CohereLLM(ILanguageModel):
    """
    Adaptador concreto para el LLM de Cohere.
    Implementa ILanguageModel para que el dominio nunca
    dependa directamente de la librería `cohere`.
    """

    def __init__(self) -> None:
        self._client = cohere.Client(api_key=settings.cohere_api_key.get_secret_value())
        self._model = settings.cohere_llm_model

    def generate(self, prompt: str) -> str:
        response = self._client.chat(
            model=self._model,
            message=prompt,
        )
        return str(response.text)
