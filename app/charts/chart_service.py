from __future__ import annotations

from app.cohort.cohort_service import CohortService


class ChartService:
    def __init__(self, cohort_service: CohortService) -> None:
        self.cohort_service = cohort_service
        self.PASTEL_PALETTE = [
        "#CDB4DB",  # lila
        "#A8DADC",  # verde agua
        "#FBC4AB",  # melocotón
        "#FAEDCD",  # crema
        "#D8E2DC",  # gris verdoso
        ]

    def build_bar_colors(self, n: int) -> list[str]:
        return [self.PASTEL_PALETTE[i % len(self.PASTEL_PALETTE)] for i in range(n)]

    def build_dashboard(self, cohort_id: str) -> dict:
        return {
            "sex_distribution": self.sex_distribution_chart(cohort_id),
            "top_conditions": self.top_conditions_chart(cohort_id),
            "top_medications": self.top_medications_chart(cohort_id),
        }

    def sex_distribution_chart(self, cohort_id: str) -> dict:
        rows = self.cohort_service.sex_distribution(cohort_id)

        labels = [row["label"] for row in rows]
        values = [row["count"] for row in rows]

        return {
            "chart_type": "donut",
            "title": "Distribución por sexo",
            "labels": labels,
            "values": values,
            "colors": ["#A8DADC", "#FBC4AB"],  # pastel
        }

    def top_conditions_chart(self, cohort_id: str, limit: int = 5) -> dict:
        rows = self.cohort_service.top_conditions(cohort_id, limit=limit)

        x = [row["label"] for row in rows]
        y = [row["count"] for row in rows]

        return {
            "chart_type": "bar",
            "title": "Condiciones más frecuentes",
            "x": x,
            "y": y,
            "colors": self.build_bar_colors(len(x)), 
        }

    def top_medications_chart(self, cohort_id: str, limit: int = 5) -> dict:
        rows = self.cohort_service.top_medications(cohort_id, limit=limit)

        x = [row["label"] for row in rows]
        y = [row["count"] for row in rows]

        return {
            "chart_type": "bar",
            "title": "Medicaciones más frecuentes",
            "x": x,
            "y": y,
            "colors": self.build_bar_colors(len(x)),  # pastel azul
        }