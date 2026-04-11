from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class SchedulingService:
    def __init__(self, base_path: str = "data/processed") -> None:
        base = Path(base_path)

        self.clinics = pd.read_csv(base / "clinics.csv")
        self.providers = pd.read_csv(base / "providers.csv")
        self.rules = pd.read_csv(base / "booking_rules.csv")
        self.slots = pd.read_csv(base / "appointment_slots.csv")

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