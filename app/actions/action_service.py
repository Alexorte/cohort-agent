from __future__ import annotations

from pathlib import Path
import pandas as pd

from app.cohort.cohort_service import CohortService


class ActionService:
    def __init__(self, cohort_service: CohortService) -> None:
        self.cohort_service = cohort_service

    def run(self, action: str, cohort_id: str, payload: dict) -> dict:
        if action == "save_cohort":
            cohort = self.cohort_service.get_cohort(cohort_id)
            return {
                "status": "ok",
                "action": action,
                "message": f"Cohorte {cohort['cohort_id']} guardada correctamente.",
            }

        if action == "export_cohort":
            cohort = self.cohort_service.get_cohort(cohort_id)
            out_dir = Path("data/processed")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{cohort_id}.csv"

            pd.DataFrame({"patient_id": cohort["patient_ids"]}).to_csv(out_path, index=False)
            return {
                "status": "ok",
                "action": action,
                "message": f"Cohorte exportada a {out_path}.",
                "file_path": str(out_path),
            }

        if action == "create_alert_draft":
            return {
                "status": "ok",
                "action": action,
                "message": "Borrador de alerta generado. Requiere validación humana.",
                "draft": payload,
            }

        raise ValueError(f"Unsupported action: {action}")