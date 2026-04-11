from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class SchedulingService:
    def __init__(self, base_path: str = "data/processed") -> None:
        self.base = Path(base_path)

        self.clinics = pd.read_csv(self.base / "clinics.csv")
        self.providers = pd.read_csv(self.base / "providers.csv")
        self.rules = pd.read_csv(self.base / "booking_rules.csv")
        self.slots = pd.read_csv(self.base / "appointment_slots.csv")

    def _get_clinic_info(self, clinic_id: str) -> dict[str, Any]:
        row = self.clinics[self.clinics["clinic_id"] == clinic_id]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def _get_provider_info(self, provider_id: str) -> dict[str, Any]:
        row = self.providers[self.providers["provider_id"] == provider_id]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def _get_rule(self, priority_level: str) -> dict[str, Any]:
        row = self.rules[self.rules["priority_level"] == priority_level]
        if row.empty:
            raise ValueError(f"No booking rule for priority level: {priority_level}")
        return row.iloc[0].to_dict()

    def _available_slots(
        self,
        province: str,
        preferred_role: str,
        min_days: int,
        max_days: int,
        limit: int = 10,
    ) -> pd.DataFrame:
        df = self.slots.copy()

        df = df[
            (df["province"] == province) &
            (df["role"] == preferred_role) &
            (df["status"] == "available")
        ].copy()

        if df.empty:
            return df

        today = pd.Timestamp("2026-04-12")
        df["date_dt"] = pd.to_datetime(df["date"])
        df["days_from_today"] = (df["date_dt"] - today).dt.days

        df = df[
            (df["days_from_today"] >= min_days) &
            (df["days_from_today"] <= max_days)
        ].copy()

        if df.empty:
            return df

        df = df.sort_values(by=["date", "start_time", "clinic_id", "provider_id"])
        return df.head(limit)

    def _reserve_slot(self, slot_id: str) -> None:
        self.slots.loc[self.slots["slot_id"] == slot_id, "status"] = "reserved"
        self._persist_slots()

    def _slot_to_dict(self, slot_row: pd.Series) -> dict[str, Any]:
        clinic = self._get_clinic_info(slot_row["clinic_id"])
        provider = self._get_provider_info(slot_row["provider_id"])

        return {
            "slot_id": slot_row["slot_id"],
            "date": slot_row["date"],
            "start_time": slot_row["start_time"],
            "end_time": slot_row["end_time"],
            "clinic_id": slot_row["clinic_id"],
            "clinic_name": clinic.get("clinic_name"),
            "clinic_address": clinic.get("address"),
            "provider_id": slot_row["provider_id"],
            "provider_name": provider.get("provider_name"),
            "provider_role": provider.get("role"),
            "province": slot_row["province"],
            "city": slot_row["city"],
            "role": slot_row["role"],
        }

    def enrich_followup_plan(self, followup_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._reload_slots()
        enriched = []

        for row in followup_plan:
            priority = row["priority_level"]
            province = row["Provincia"]

            rule = self._get_rule(priority)
            booking_mode = rule["booking_mode"]
            preferred_role = rule["preferred_role"]
            min_days = int(rule["target_window_days_min"])
            max_days = int(rule["target_window_days_max"])

            updated_row = {**row}
            updated_row["booking_mode"] = booking_mode
            updated_row["appointment_status"] = None
            updated_row["booked_slot_id"] = None
            updated_row["booked_date"] = None
            updated_row["booked_time"] = None
            updated_row["booked_clinic"] = None
            updated_row["booked_provider"] = None
            updated_row["suggested_slots"] = []

            if priority == "Alta":
                candidates = self._available_slots(
                    province=province,
                    preferred_role=preferred_role,
                    min_days=min_days,
                    max_days=max_days,
                    limit=1,
                )

                if not candidates.empty:
                    slot = candidates.iloc[0]
                    self._reserve_slot(slot["slot_id"])
                    slot_info = self._slot_to_dict(slot)

                    updated_row["appointment_status"] = "auto_booked"
                    updated_row["booked_slot_id"] = slot_info["slot_id"]
                    updated_row["booked_date"] = slot_info["date"]
                    updated_row["booked_time"] = f'{slot_info["start_time"]}-{slot_info["end_time"]}'
                    updated_row["booked_clinic"] = slot_info["clinic_id"]
                    updated_row["booked_clinic_name"] = slot_info["clinic_name"]
                    updated_row["booked_city"] = slot_info["city"]
                    updated_row["booked_address"] = slot_info["clinic_address"]
                    updated_row["booked_provider"] = slot_info["provider_id"]
                    updated_row["booked_provider_name"] = slot_info["provider_name"]
                    updated_row["booked_provider_role"] = slot_info["provider_role"]
                else:
                    updated_row["appointment_status"] = "needs_manual_review"

            elif priority == "Media":
                candidates = self._available_slots(
                    province=province,
                    preferred_role=preferred_role,
                    min_days=min_days,
                    max_days=max_days,
                    limit=3,
                )

                if not candidates.empty:
                    updated_row["appointment_status"] = "awaiting_user_confirmation"
                    updated_row["suggested_slots"] = [
                        self._slot_to_dict(slot)
                        for _, slot in candidates.iterrows()
                    ]
                else:
                    updated_row["appointment_status"] = "no_suggestions_available"

            else:
                updated_row["appointment_status"] = "routine_followup"

            enriched.append(updated_row)

        return enriched

    def _persist_slots(self) -> None:
        self.slots.to_csv(self.base / "appointment_slots.csv", index=False)
    
    def cancel_booking(self, slot_id: str) -> dict[str, Any]:
        self._reload_slots()
        slot_rows = self.slots[self.slots["slot_id"] == slot_id]
        if slot_rows.empty:
            raise ValueError(f"Slot no encontrado: {slot_id}")

        self.slots.loc[self.slots["slot_id"] == slot_id, "status"] = "available"
        self._persist_slots()

        slot = slot_rows.iloc[0]
        return {
            "status": "cancelled",
            "slot_id": slot_id,
            "date": slot["date"],
            "start_time": slot["start_time"],
            "end_time": slot["end_time"],
            "clinic_id": slot["clinic_id"],
            "provider_id": slot["provider_id"],
        }

    def reschedule_high_priority(self, current_slot_id: str, province: str) -> dict[str, Any]:
        current_rows = self.slots[self.slots["slot_id"] == current_slot_id]
        if current_rows.empty:
            raise ValueError(f"Slot actual no encontrado: {current_slot_id}")

        current_slot = current_rows.iloc[0]

        rule = self._get_rule("Alta")
        preferred_role = rule["preferred_role"]
        min_days = int(rule["target_window_days_min"])
        max_days = int(rule["target_window_days_max"])

        candidates = self._available_slots(
            province=province,
            preferred_role=preferred_role,
            min_days=min_days,
            max_days=max_days,
            limit=200,
        )

        if not candidates.empty:
            candidates = candidates[candidates["slot_id"] != current_slot_id].copy()

        if candidates.empty:
            return {
                "status": "needs_manual_review",
                "message": "No se ha encontrado un nuevo hueco para reprogramar.",
            }

        # Construimos una clave temporal para comparar con la cita actual
        current_dt = pd.to_datetime(f'{current_slot["date"]} {current_slot["start_time"]}')
        candidates["slot_dt"] = pd.to_datetime(candidates["date"] + " " + candidates["start_time"])

        # Queremos solo citas posteriores a la actual
        later_candidates = candidates[candidates["slot_dt"] > current_dt].copy()

        if later_candidates.empty:
            return {
                "status": "needs_manual_review",
                "message": "No se ha encontrado una cita posterior disponible para reprogramar.",
            }

        later_candidates = later_candidates.sort_values(
            by=["slot_dt", "clinic_id", "provider_id"]
        )

        new_slot = later_candidates.iloc[0]
        new_slot_info = self._slot_to_dict(new_slot)

        # Libera la actual y reserva la nueva
        self.slots.loc[self.slots["slot_id"] == current_slot_id, "status"] = "available"
        self.slots.loc[self.slots["slot_id"] == new_slot["slot_id"], "status"] = "reserved"
        self._persist_slots()

        return {
            "status": "rescheduled",
            "old_slot_id": current_slot_id,
            "new_slot_id": new_slot_info["slot_id"],
            "booked_date": new_slot_info["date"],
            "booked_time": f'{new_slot_info["start_time"]}-{new_slot_info["end_time"]}',
            "booked_clinic": new_slot_info["clinic_id"],
            "booked_clinic_name": new_slot_info.get("clinic_name"),
            "booked_city": new_slot_info.get("city"),
            "booked_address": new_slot_info.get("clinic_address"),
            "booked_provider": new_slot_info["provider_id"],
            "booked_provider_name": new_slot_info.get("provider_name"),
            "booked_provider_role": new_slot_info.get("provider_role"),
        }

    def _reload_slots(self) -> None:
        self.slots = pd.read_csv(self.base / "appointment_slots.csv")
    
    def confirm_suggested_slot(self, patient_id: int, slot_id: str) -> dict[str, Any]:
        # Recomendable si ya has añadido recarga desde disco
        self.slots = pd.read_csv(self.base / "appointment_slots.csv")

        slot_rows = self.slots[self.slots["slot_id"] == slot_id]
        if slot_rows.empty:
            raise ValueError(f"Slot no encontrado: {slot_id}")

        slot = slot_rows.iloc[0]

        if slot["status"] != "available":
            return {
                "status": "slot_unavailable",
                "message": "La propuesta ya no está disponible.",
            }

        # Opcional, pero útil: asegurar que ese slot es válido para prioridad media
        priority_eligible = str(slot.get("priority_eligible", ""))
        if "Media" not in priority_eligible:
            return {
                "status": "invalid_slot",
                "message": "El slot seleccionado no es válido para prioridad media.",
            }

        self.slots.loc[self.slots["slot_id"] == slot_id, "status"] = "reserved"
        self._persist_slots()

        slot_info = self._slot_to_dict(slot)

        return {
            "status": "confirmed",
            "patient_id": patient_id,
            "slot_id": slot_info["slot_id"],
            "booked_date": slot_info["date"],
            "booked_time": f'{slot_info["start_time"]}-{slot_info["end_time"]}',
            "booked_clinic": slot_info["clinic_id"],
            "booked_clinic_name": slot_info.get("clinic_name"),
            "booked_city": slot_info.get("city"),
            "booked_address": slot_info.get("clinic_address"),
            "booked_provider": slot_info["provider_id"],
            "booked_provider_name": slot_info.get("provider_name"),
            "booked_provider_role": slot_info.get("provider_role"),
        }