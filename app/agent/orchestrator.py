from __future__ import annotations

from app.actions.action_service import ActionService
from app.agent.guardrails import Guardrails
from app.agent.intent_parser import IntentParser
from app.agent.memory_store import MemoryStore
from app.agent.response_builder import ResponseBuilder
from app.cohort.cohort_service import CohortService
from app.charts.chart_service import ChartService

class Orchestrator:
    def __init__(
        self,
        memory: MemoryStore,
        parser: IntentParser,
        guardrails: Guardrails,
        cohort_service: CohortService,
        action_service: ActionService,
        response_builder: ResponseBuilder,
        chart_service: ChartService,
    ) -> None:
        self.memory = memory
        self.parser = parser
        self.guardrails = guardrails
        self.cohort_service = cohort_service
        self.action_service = action_service
        self.response_builder = response_builder
        self.chart_service = chart_service

    def _append_warning_text(self, base_message: str, unknown_terms: list[str]) -> str:
        if not unknown_terms:
            return base_message

        return f"{base_message} He detectado alguna palabra no reconocida: {', '.join(unknown_terms)}."
    def handle_message(self, session_id: str, message: str):
        state = self.memory.get(session_id)
        has_active_cohort = state["active_cohort_id"] is not None

        parsed = self.parser.parse(message, has_active_cohort=has_active_cohort)
        filters = self.guardrails.validate_filters(parsed.filters)

        if parsed.intent == "create_cohort":
            cohort = self.cohort_service.create_cohort(filters)
            self.memory.update(
                session_id,
                active_cohort_id=cohort["cohort_id"],
                active_cohort_definition=cohort["definition"],
                last_user_intent=parsed.intent,
            )
            #Diferenciar singular y plural en la respuesta
            count = cohort["size"]
            label = "pacientes" if count != 1 else "paciente"
            
            return self.response_builder.build_text(
                session_id=session_id,
                message=self._append_warning_text(
                    f"He creado una cohorte con {count} {label}.",
                    parsed.unknown_terms,
                ),
                cohort_id=cohort["cohort_id"],
                cohort_size=cohort["size"],
                filters_applied=cohort["definition"],
                tables_used=["patients", "conditions", "allergies", "medications"],
                data={"patient_ids": cohort["patient_ids"], "charts": self.chart_service.build_dashboard(cohort["cohort_id"]),},
                warnings=parsed.warnings,
                unknown_terms=parsed.unknown_terms,
            )

        if parsed.intent == "refine_cohort":
            if not state["active_cohort_id"]:
                return self.response_builder.build_text(
                    session_id=session_id,
                    message="No hay una cohorte activa para refinar.",
                )

            cohort = self.cohort_service.refine_cohort(state["active_cohort_id"], filters)
            self.memory.update(
                session_id,
                active_cohort_id=cohort["cohort_id"],
                active_cohort_definition=cohort["definition"],
                last_user_intent=parsed.intent,
            )
            #Diferenciar singular y plural en la respuesta
            count = cohort["size"]
            label = "pacientes" if count != 1 else "paciente"
            
            return self.response_builder.build_text(
                session_id=session_id,
                message=self._append_warning_text(
                    f"He refinado la cohorte. Ahora tiene {count} {label}.",
                    parsed.unknown_terms,
                ),
                cohort_id=cohort["cohort_id"],
                cohort_size=cohort["size"],
                filters_applied=cohort["definition"],
                tables_used=["patients", "conditions", "allergies", "medications"],
                data={"patient_ids": cohort["patient_ids"], "charts": self.chart_service.build_dashboard(cohort["cohort_id"])},
                warnings=parsed.warnings,
                unknown_terms=parsed.unknown_terms,
            )

        if parsed.intent == "get_stats":
            if not state["active_cohort_id"]:
                return self.response_builder.build_text(
                    session_id=session_id,
                    message="No hay una cohorte activa para calcular estadísticas.",
                )

            cohort_id = state["active_cohort_id"]
            summary = self.cohort_service.compute_summary(cohort_id)
            top_conditions = self.cohort_service.top_conditions(cohort_id)
            top_medications = self.cohort_service.top_medications(cohort_id)

            return self.response_builder.build_text(
                session_id=session_id,
                message=self._append_warning_text(
                    "Aquí tienes el resumen de la cohorte activa.",
                    parsed.unknown_terms,
                ),
                cohort_id=cohort_id,
                cohort_size=summary.get("total_patients"),
                filters_applied=state["active_cohort_definition"],
                tables_used=["patients", "conditions", "medications"],
                data={
                    "summary": summary,
                    "top_conditions": top_conditions, 
                    "top_medications": top_medications,
                    "patient_ids": cohort["patient_ids"],
                    "charts": self.chart_service.build_dashboard(cohort["cohort_id"]),
                },
                warnings=parsed.warnings,
                unknown_terms=parsed.unknown_terms,
            )
        
        if parsed.intent == "get_chart":
            if not state["active_cohort_id"]:
                return self.response_builder.build_text(
                    session_id=session_id,
                    message="No hay una cohorte activa para mostrar gráficas.",
                    warnings=parsed.warnings,
                    unknown_terms=parsed.unknown_terms,
                )

            cohort_id = state["active_cohort_id"]
            cohort = self.cohort_service.get_cohort(cohort_id)
            dashboard = self.chart_service.build_dashboard(cohort_id)

            selected_chart = dashboard.get(parsed.chart) if parsed.chart else None

            return self.response_builder.build_text(
                session_id=session_id,
                message="Aquí tienes las gráficas de la cohorte activa.",
                cohort_id=cohort_id,
                cohort_size=cohort["size"],
                filters_applied=state["active_cohort_definition"],
                tables_used=["patients", "conditions", "medications"],
                data={
                    "chart": selected_chart,
                    "charts": dashboard,
                    "patient_ids": cohort["patient_ids"],
                },
                warnings=parsed.warnings,
                unknown_terms=parsed.unknown_terms,
            )

        if parsed.intent == "run_action":
            if not state["active_cohort_id"]:
                return self.response_builder.build_text(
                    session_id=session_id,
                    message="No hay una cohorte activa sobre la que ejecutar la acción.",
                )

            result = self.action_service.run(parsed.action, state["active_cohort_id"], parsed.payload)
            return self.response_builder.build_text(
                session_id=session_id,
                message=result["message"],
                cohort_id=state["active_cohort_id"],
                filters_applied=state["active_cohort_definition"],
                data=result,
                warnings=parsed.warnings,
                unknown_terms=parsed.unknown_terms,
            )

        return self.response_builder.build_text(
            session_id=session_id,
            message=self._append_warning_text(
                "No he podido interpretar la petición con suficiente fiabilidad.",
                parsed.unknown_terms,
            ),
            warnings=parsed.warnings,
            unknown_terms=parsed.unknown_terms,
        )