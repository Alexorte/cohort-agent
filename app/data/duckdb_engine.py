from __future__ import annotations

from pathlib import Path
import duckdb

from app.config.settings import settings


class DuckDBEngine:
    def __init__(self) -> None:
        self.conn = duckdb.connect(database=":memory:")
        self._load_views()

    def _csv_path(self, filename: str) -> str:
        return str(Path(settings.data_dir) / filename)

    def _load_views(self) -> None:
        self.conn.execute(f"""
            CREATE OR REPLACE VIEW patients AS
            SELECT
                PacienteID,
                Genero,
                Edad,
                Provincia,
                Latitud,
                Longitud
            FROM read_csv_auto('{self._csv_path(settings.patients_csv)}', HEADER=TRUE);
        """)

        self.conn.execute(f"""
            CREATE OR REPLACE VIEW allergies AS
            SELECT
                PacienteID,
                Fecha_diagnostico,
                Codigo_SNOMED,
                Descripcion
            FROM read_csv_auto('{self._csv_path(settings.allergies_csv)}', HEADER=TRUE);
        """)

        self.conn.execute(f"""
            CREATE OR REPLACE VIEW conditions AS
            SELECT
                PacienteID,
                Fecha_inicio,
                Fecha_fin,
                Codigo_SNOMED,
                Descripcion
            FROM read_csv_auto('{self._csv_path(settings.conditions_csv)}', HEADER=TRUE);
        """)

        self.conn.execute(f"""
            CREATE OR REPLACE VIEW procedures AS
            SELECT
                PacienteID,
                Fecha_inicio,
                Fecha_fin,
                Codigo_SNOMED,
                Descripcion
            FROM read_csv_auto('{self._csv_path(settings.procedures_csv)}', HEADER=TRUE);
        """)

        self.conn.execute(f"""
            CREATE OR REPLACE VIEW encounters AS
            SELECT
                PacienteID,
                Tipo_encuentro,
                Fecha_inicio,
                Fecha_fin
            FROM read_csv_auto('{self._csv_path(settings.encounters_csv)}', HEADER=TRUE);
        """)

        self.conn.execute(f'''
            CREATE OR REPLACE VIEW medications AS
            SELECT
                PacienteID,
                "Fecha de inicio" AS Fecha_inicio,
                "Fecha de fin" AS Fecha_fin,
                "Código" AS Codigo,
                Nombre,
                Dosis,
                Frecuencia,
                "Vía de administración" AS Via_administracion
            FROM read_csv_auto('{self._csv_path(settings.medications_csv)}', HEADER=TRUE);
        ''')

    def query(self, sql: str, params: list | None = None):
        if params is None:
            params = []
        return self.conn.execute(sql, params).fetchdf()