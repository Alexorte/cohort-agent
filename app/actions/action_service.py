from __future__ import annotations

from pathlib import Path
import pandas as pd

from app.cohort.cohort_service import CohortService
from app.scheduling.scheduling_service import SchedulingService

class ActionService:
    def __init__(
        self,
        cohort_service: CohortService,
        scheduling_service: SchedulingService,
    ) -> None:
        self.cohort_service = cohort_service
        self.scheduling_service = scheduling_service

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

        if action == "prepare_followup_plan":
            base_plan = self.cohort_service.build_followup_plan(cohort_id)
            enriched_plan = self.scheduling_service.enrich_followup_plan(base_plan)

            auto_booked = sum(1 for row in enriched_plan if row["appointment_status"] == "auto_booked")
            proposed = sum(1 for row in enriched_plan if row["appointment_status"] == "awaiting_user_confirmation")

            return {
                "status": "ok",
                "action": action,
                "message": (
                    "He preparado un plan de seguimiento clínico para la cohorte activa. "
                    f"Reservadas automáticamente: {auto_booked}. "
                    f"Con propuestas pendientes: {proposed}."
                ),
                "followup_plan": enriched_plan,
            }

        raise ValueError(f"Unsupported action: {action}")