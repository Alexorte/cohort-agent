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

app = FastAPI(title=settings.app_name, version=settings.app_version)

engine = DuckDBEngine()
memory = MemoryStore()
parser = IntentParser()
guardrails = Guardrails()
cohort_service = CohortService(engine)
action_service = ActionService(cohort_service)
response_builder = ResponseBuilder()

orchestrator = Orchestrator(
    memory=memory,
    parser=parser,
    guardrails=guardrails,
    cohort_service=cohort_service,
    action_service=action_service,
    response_builder=response_builder,
)


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