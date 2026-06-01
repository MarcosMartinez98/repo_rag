# src/rag_course/application/evaluate_use_case.py
"""
Evaluación automática del pipeline RAG con RAGAS.
"""

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, faithfulness

from rag_course.application.query_use_case import QueryUseCase
from rag_course.domain.models import QueryResult


class EvaluateUseCase:
    """
    Evalúa el sistema RAG contra un conjunto de preguntas de prueba.
    Requiere ground_truth solo para context_recall; el resto es sin-referencia.
    """

    def __init__(self, query_use_case: QueryUseCase) -> None:
        self._query = query_use_case

    def execute(self, test_questions: list[str]) -> dict[str, float]:
        results: list[QueryResult] = []
        for q in test_questions:
            results.append(self._query.execute(q))

        # Construir el dataset en el formato que RAGAS espera
        dataset = Dataset.from_dict(
            {
                "question": [r.query for r in results],
                "answer": [r.answer for r in results],
                "contexts": [[c.content for c in r.source_chunks] for r in results],
            }
        )

        scores = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
        )

        return {
            "faithfulness": round(float(scores["faithfulness"]), 4),
            "answer_relevancy": round(float(scores["answer_relevancy"]), 4),
            "context_precision": round(float(scores["context_precision"]), 4),
        }
