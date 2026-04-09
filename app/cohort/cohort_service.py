from __future__ import annotations

import uuid
from typing import Any

from app.data.duckdb_engine import DuckDBEngine


class CohortService:
    def __init__(self, engine: DuckDBEngine) -> None:
        self.engine = engine
        self._cohorts: dict[str, dict[str, Any]] = {}

    def create_cohort(self, filters: dict[str, Any]) -> dict[str, Any]:
        patient_ids = self._run_patient_filter_query(filters)
        cohort_id = f"cohort_{uuid.uuid4().hex[:8]}"
        cohort = {
            "cohort_id": cohort_id,
            "patient_ids": patient_ids,
            "size": len(patient_ids),
            "definition": filters,
        }
        self._cohorts[cohort_id] = cohort
        return cohort

    def refine_cohort(self, cohort_id: str, filters: dict[str, Any]) -> dict[str, Any]:
        base = self._cohorts.get(cohort_id)
        if not base:
            raise ValueError(f"Cohorte no encontrada: {cohort_id}")

        patient_ids = self._run_patient_filter_query(filters, base_ids=base["patient_ids"])
        new_cohort_id = f"cohort_{uuid.uuid4().hex[:8]}"
        merged_definition = {**base["definition"], **filters}

        cohort = {
            "cohort_id": new_cohort_id,
            "patient_ids": patient_ids,
            "size": len(patient_ids),
            "definition": merged_definition,
        }
        self._cohorts[new_cohort_id] = cohort
        return cohort

    def get_cohort(self, cohort_id: str) -> dict[str, Any]:
        cohort = self._cohorts.get(cohort_id)
        if not cohort:
            raise ValueError(f"Cohorte no encontrada: {cohort_id}")
        return cohort

    def compute_summary(self, cohort_id: str) -> dict[str, Any]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return {
                "total_patients": 0,
                "mean_age": None,
                "female_pct": None,
                "male_pct": None,
            }

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))
        sql = f"""
        SELECT
            COUNT(*) AS total_patients,
            AVG(Edad) AS mean_age,
            100.0 * SUM(CASE WHEN lower(Genero) = 'femenino' THEN 1 ELSE 0 END) / COUNT(*) AS female_pct,
            100.0 * SUM(CASE WHEN lower(Genero) = 'masculino' THEN 1 ELSE 0 END) / COUNT(*) AS male_pct
        FROM patients
        WHERE PacienteID IN ({placeholders})
        """
        df = self.engine.query(sql, cohort["patient_ids"])
        return df.to_dict(orient="records")[0]

    def top_conditions(self, cohort_id: str, limit: int = 5) -> list[dict[str, Any]]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return []

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))
        sql = f"""
        SELECT Descripcion AS label, COUNT(*) AS count
        FROM conditions
        WHERE PacienteID IN ({placeholders})
        GROUP BY Descripcion
        ORDER BY count DESC
        LIMIT {limit}
        """
        df = self.engine.query(sql, cohort["patient_ids"])
        return df.to_dict(orient="records")

    def top_medications(self, cohort_id: str, limit: int = 5) -> list[dict[str, Any]]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return []

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))
        sql = f"""
        SELECT Nombre AS label, COUNT(*) AS count
        FROM medications
        WHERE PacienteID IN ({placeholders})
        GROUP BY Nombre
        ORDER BY count DESC
        LIMIT {limit}
        """
        df = self.engine.query(sql, cohort["patient_ids"])
        return df.to_dict(orient="records")

    def _run_patient_filter_query(
        self,
        filters: dict[str, Any],
        base_ids: list[int] | None = None,
    ) -> list[int]:
        where_clauses = ["1=1"]
        params: list[Any] = []

        if base_ids is not None:
            if len(base_ids) == 0:
                return []

            placeholders = ",".join(["?"] * len(base_ids))
            where_clauses.append(f"p.PacienteID IN ({placeholders})")
            params.extend(base_ids)

        has_allergies = filters.get("has_allergies")
        if has_allergies:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM allergies a
                    WHERE a.PacienteID = p.PacienteID
                )
            """)

        has_conditions = filters.get("has_conditions")
        if has_conditions:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM conditions c
                    WHERE c.PacienteID = p.PacienteID
                )
            """)

        has_medications = filters.get("has_medications")
        if has_medications:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM medications m
                    WHERE m.PacienteID = p.PacienteID
                )
            """)

        age_range = filters.get("age_range")
        if age_range:
            min_op = ">=" if age_range.get("include_min", True) else ">"
            max_op = "<=" if age_range.get("include_max", True) else "<"
            where_clauses.append(f"p.Edad {min_op} ?")
            params.append(age_range["min"])
            where_clauses.append(f"p.Edad {max_op} ?")
            params.append(age_range["max"])

        age_filter = filters.get("age")
        if age_filter:
            where_clauses.append(f"p.Edad {age_filter['operator']} ?")
            params.append(age_filter["value"])

        sex = filters.get("sex")
        if sex:
            where_clauses.append("lower(p.Genero) = lower(?)")
            params.append(sex)

        include_conditions = filters.get("include_conditions", [])
        for condition in include_conditions:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM conditions c
                    WHERE c.PacienteID = p.PacienteID
                      AND lower(c.Descripcion) LIKE lower(?)
                )
            """)
            params.append(f"%{condition}%")

        exclude_conditions = filters.get("exclude_conditions", [])
        for condition in exclude_conditions:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM conditions c
                    WHERE c.PacienteID = p.PacienteID
                      AND lower(c.Descripcion) LIKE lower(?)
                )
            """)
            params.append(f"%{condition}%")

        include_allergies = filters.get("include_allergies", [])
        for allergy in include_allergies:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM allergies a
                    WHERE a.PacienteID = p.PacienteID
                      AND lower(a.Descripcion) LIKE lower(?)
                )
            """)
            params.append(f"%{allergy}%")

        exclude_allergies = filters.get("exclude_allergies", [])
        for allergy in exclude_allergies:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM allergies a
                    WHERE a.PacienteID = p.PacienteID
                      AND lower(a.Descripcion) LIKE lower(?)
                )
            """)
            params.append(f"%{allergy}%")

        include_medications = filters.get("include_medications", [])
        for medication in include_medications:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM medications m
                    WHERE m.PacienteID = p.PacienteID
                      AND lower(m.Nombre) LIKE lower(?)
                )
            """)
            params.append(f"%{medication}%")

        exclude_medications = filters.get("exclude_medications", [])
        for medication in exclude_medications:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM medications m
                    WHERE m.PacienteID = p.PacienteID
                      AND lower(m.Nombre) LIKE lower(?)
                )
            """)
            params.append(f"%{medication}%")

        sql = f"""
        SELECT DISTINCT p.PacienteID
        FROM patients p
        WHERE {" AND ".join(where_clauses)}
        ORDER BY p.PacienteID
        """

        df = self.engine.query(sql, params)
        if "PacienteID" not in df.columns:
            return []
        return df["PacienteID"].tolist()