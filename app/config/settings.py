from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Datathon Cohort Agent"
    app_version: str = "0.1.0"

    data_dir: str = "data/raw"
    patients_csv: str = "cohorte_pacientes.csv"
    allergies_csv: str = "cohorte_alegias.csv"
    conditions_csv: str = "cohorte_condiciones.csv"
    procedures_csv: str = "cohorte_procedimientos.csv"
    encounters_csv: str = "cohorte_encuentros.csv"
    medications_csv: str = "cohorte_medicationes.csv"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()