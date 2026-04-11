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
        SELECT Descripcion AS label, COUNT(DISTINCT PacienteID) AS count
        FROM conditions
        WHERE PacienteID IN ({placeholders})
        GROUP BY Descripcion
        ORDER BY count DESC, label ASC
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
        SELECT Nombre AS label, COUNT(DISTINCT PacienteID) AS count
        FROM medications
        WHERE PacienteID IN ({placeholders})
        GROUP BY Nombre
        ORDER BY count DESC, label ASC
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

        table_filters = filters.get("table_filters", [])
        for tf in table_filters:
            table = tf["table"]
            column = tf["column"]
            operator = tf["operator"]
            value = tf["value"]
            value_type = tf.get("value_type", "text")

            alias_map = {
                "allergies": "a",
                "conditions": "c",
                "medications": "m",
                "encounters": "e",
                "procedures": "pr",
            }

            alias = alias_map[table]

            if value_type == "date":
                where_clauses.append(f"""
                    EXISTS (
                        SELECT 1
                        FROM {table} {alias}
                        WHERE {alias}.PacienteID = p.PacienteID
                        AND CAST({alias}.{column} AS DATE) {operator} CAST(? AS DATE)
                    )
                """)
                params.append(value)

            elif value_type == "text":
                where_clauses.append(f"""
                    EXISTS (
                        SELECT 1
                        FROM {table} {alias}
                        WHERE {alias}.PacienteID = p.PacienteID
                        AND lower({alias}.{column}) = lower(?)
                    )
                """)
                params.append(value)

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
                      AND lower(c.Descripcion) = lower(?)
                )
            """)
            params.append(condition)

        exclude_conditions = filters.get("exclude_conditions", [])
        for condition in exclude_conditions:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM conditions c
                    WHERE c.PacienteID = p.PacienteID
                      AND lower(c.Descripcion) = lower(?)
                )
            """)
            params.append(condition)

        include_allergies = filters.get("include_allergies", [])
        for allergy in include_allergies:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM allergies a
                    WHERE a.PacienteID = p.PacienteID
                      AND lower(a.Descripcion) = lower(?)
                )
            """)
            params.append(allergy)

        exclude_allergies = filters.get("exclude_allergies", [])
        for allergy in exclude_allergies:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM allergies a
                    WHERE a.PacienteID = p.PacienteID
                      AND lower(a.Descripcion) = lower(?)
                )
            """)
            params.append(allergy)

        include_medications = filters.get("include_medications", [])
        for medication in include_medications:
            where_clauses.append("""
                EXISTS (
                    SELECT 1
                    FROM medications m
                    WHERE m.PacienteID = p.PacienteID
                      AND lower(m.Nombre) = lower(?)
                )
            """)
            params.append(medication)

        exclude_medications = filters.get("exclude_medications", [])
        for medication in exclude_medications:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM medications m
                    WHERE m.PacienteID = p.PacienteID
                      AND lower(m.Nombre) = lower(?)
                )
            """)
            params.append(medication)

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
    
    def sex_distribution(self, cohort_id: str) -> list[dict[str, int | str]]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return []

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))
        sql = f"""
        SELECT Genero AS label, COUNT(*) AS count
        FROM patients
        WHERE PacienteID IN ({placeholders})
        GROUP BY Genero
        ORDER BY count DESC, label ASC
        """
        df = self.engine.query(sql, cohort["patient_ids"])
        return df.to_dict(orient="records")

    def build_followup_plan(self, cohort_id: str) -> list[dict[str, Any]]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return []

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))

        sql = f"""
        WITH cohort_patients AS (
            SELECT
                p.PacienteID,
                p.Edad,
                p.Genero,
                p.Provincia
            FROM patients p
            WHERE p.PacienteID IN ({placeholders})
        ),
        cond AS (
            SELECT PacienteID, COUNT(*) AS num_conditions
            FROM conditions
            WHERE PacienteID IN ({placeholders})
            GROUP BY PacienteID
        ),
        med AS (
            SELECT PacienteID, COUNT(*) AS num_medications
            FROM medications
            WHERE PacienteID IN ({placeholders})
            GROUP BY PacienteID
        ),
        alg AS (
            SELECT PacienteID, COUNT(*) AS num_allergies
            FROM allergies
            WHERE PacienteID IN ({placeholders})
            GROUP BY PacienteID
        ),
        enc AS (
            SELECT PacienteID, COUNT(*) AS num_encounters
            FROM encounters
            WHERE PacienteID IN ({placeholders})
            GROUP BY PacienteID
        )
        SELECT
            cp.PacienteID,
            cp.Edad,
            cp.Genero,
            cp.Provincia,
            COALESCE(cond.num_conditions, 0) AS num_conditions,
            COALESCE(med.num_medications, 0) AS num_medications,
            COALESCE(alg.num_allergies, 0) AS num_allergies,
            COALESCE(enc.num_encounters, 0) AS num_encounters
        FROM cohort_patients cp
        LEFT JOIN cond ON cp.PacienteID = cond.PacienteID
        LEFT JOIN med ON cp.PacienteID = med.PacienteID
        LEFT JOIN alg ON cp.PacienteID = alg.PacienteID
        LEFT JOIN enc ON cp.PacienteID = enc.PacienteID
        ORDER BY cp.PacienteID
        """

        params = (
            cohort["patient_ids"]
            + cohort["patient_ids"]
            + cohort["patient_ids"]
            + cohort["patient_ids"]
            + cohort["patient_ids"]
        )

        df = self.engine.query(sql, params)
        rows = df.to_dict(orient="records")

        enriched_rows = []
        for row in rows:
            score = 0
            reasons = []

            # 1. Edad: Se mantiene igual, es un buen factor de riesgo.
            if row["Edad"] > 75:
                score += 2
                reasons.append("Edad > 75")

            # 2. Condiciones: Ajustado a pluripatología (>= 4)
            if row["num_conditions"] >= 4:
                score += 2
                reasons.append("Pluripatología (>= 4 condiciones)")

            # 3. Medicación: Ajustado a la definición real de polimedicación (>= 5)
            if row["num_medications"] >= 5:
                score += 2
                reasons.append("Polimedicación (>= 5 fármacos)")

            # 4. Alergias: Mantenemos el punto, pero es el factor menos determinante de prioridad crónica
            if row["num_allergies"] >= 1:
                score += 1
                reasons.append("Tiene alergias registradas")

            # 5. Encuentros: Ajustado a hiperfrecuentación (>= 4 visitas)
            if row["num_encounters"] >= 4:
                score += 1
                reasons.append("Alta frecuentación (>= 4 encuentros)")

            # --- NUEVOS UMBRALES DE PRIORIDAD ---
            if score >= 5:
                priority_level = "Alta"
                suggested_action = "Valoración clínica prioritaria"
            elif score >= 3:
                priority_level = "Media"
                suggested_action = "Seguimiento por enfermería"
            else:
                priority_level = "Baja"
                suggested_action = "Seguimiento rutinario"

            enriched_rows.append({
                "PacienteID": row["PacienteID"],
                "Edad": row["Edad"],
                "Genero": row["Genero"],
                "Provincia": row["Provincia"],
                "num_conditions": row["num_conditions"],
                "num_medications": row["num_medications"],
                "num_allergies": row["num_allergies"],
                "num_encounters": row["num_encounters"],
                "priority_score": score,
                "priority_level": priority_level,
                "priority_reason": ", ".join(reasons) if reasons else "Sin factores de riesgo destacados",
                "suggested_action": suggested_action,
            })

        enriched_rows.sort(
            key=lambda x: (-x["priority_score"], x["PacienteID"])
        )

        return enriched_rows
    
    def patient_summary(self, cohort_id: str) -> list[dict]:
        cohort = self.get_cohort(cohort_id)
        if not cohort["patient_ids"]:
            return []

        placeholders = ",".join(["?"] * len(cohort["patient_ids"]))
        sql = f"""
        SELECT PacienteID, Edad, Genero, Provincia
        FROM patients
        WHERE PacienteID IN ({placeholders})
        ORDER BY PacienteID
        """
        df = self.engine.query(sql, cohort["patient_ids"])
        return df.to_dict(orient="records")