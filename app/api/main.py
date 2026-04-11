from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.actions.action_service import ActionService
from app.agent.guardrails import Guardrails
from app.agent.intent_parser import IntentParser
from app.agent.memory_store import MemoryStore
from app.agent.orchestrator import Orchestrator
from app.agent.response_builder import ResponseBuilder
from app.cohort.cohort_service import CohortService
from app.config.settings import settings
from app.data.duckdb_engine import DuckDBEngine
from app.models.api_models import ChatRequest, ChatResponse
from app.charts.chart_service import ChartService
from fastapi.middleware.cors import CORSMiddleware
from app.scheduling.scheduling_service import SchedulingService
from pydantic import BaseModel

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = DuckDBEngine()
memory = MemoryStore()
parser = IntentParser()
guardrails = Guardrails()
cohort_service = CohortService(engine)
scheduling_service = SchedulingService(base_path="data/processed")
action_service = ActionService(cohort_service, scheduling_service)
response_builder = ResponseBuilder()
chart_service = ChartService(cohort_service)

orchestrator = Orchestrator(
    memory=memory,
    parser=parser,
    guardrails=guardrails,
    cohort_service=cohort_service,
    action_service=action_service,
    response_builder=response_builder,
    chart_service=chart_service
)

class CancelBookingRequest(BaseModel):
    patient_id: int
    slot_id: str

class RescheduleBookingRequest(BaseModel):
    patient_id: int
    current_slot_id: str
    province: str

class ConfirmSuggestedSlotRequest(BaseModel):
    patient_id: int
    slot_id: str

@app.get("/")
def root():
    return {
        "message": "Datathon Cohort Agent activo",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return orchestrator.handle_message(
            session_id=request.session_id,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc

@app.post("/actions/cancel-booking")
def cancel_booking(request: CancelBookingRequest):
    result = scheduling_service.cancel_booking(request.slot_id)
    return {
        "status": "ok",
        "patient_id": request.patient_id,
        **result,
    }

@app.post("/actions/reschedule-booking")
def reschedule_booking(request: RescheduleBookingRequest):
    result = scheduling_service.reschedule_high_priority(
        current_slot_id=request.current_slot_id,
        province=request.province,
    )
    return {
        "status": "ok",
        "patient_id": request.patient_id,
        **result,
    }

@app.post("/actions/confirm-suggested-slot")
def confirm_suggested_slot(request: ConfirmSuggestedSlotRequest):
    result = scheduling_service.confirm_suggested_slot(
        patient_id=request.patient_id,
        slot_id=request.slot_id,
    )
    return result