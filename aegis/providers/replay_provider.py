# aegis/providers/replay_provider.py
"""
A mock BackendProvider for replaying agent tasks from a log.
"""
from typing import List, Dict, Any, Optional, Type, Union
import os

from pydantic import BaseModel

from aegis.exceptions import PlannerError
from aegis.providers.base import BackendProvider
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.tracing import log_generation


class ReplayProvider(BackendProvider):
    """
    A mock provider that serves pre-recorded planner outputs from a replay log.
    """

    def __init__(self, planner_outputs: List[Dict[str, Any]]):
        self.planner_outputs = planner_outputs
        self.call_count = 0

    async def get_structured_completion(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[BaseModel],
        runtime_config: RuntimeExecutionConfig,
    ) -> BaseModel:
        """
        Returns the next pre-recorded plan instead of calling an LLM.
        """
        if self.call_count >= len(self.planner_outputs):
            raise PlannerError("ReplayProvider ran out of planner outputs to serve.")

        plan_data = self.planner_outputs[self.call_count]
        self.call_count += 1

        # The 'plan' key was added during the replay log creation
        return response_model.model_validate(plan_data["plan"])
        try:
            # Try to pull metadata from the replay record if present
            _rec = (
                locals().get("record")
                or locals().get("entry")
                or locals().get("item")
                or {}
            )
            _model = None
            if isinstance(_rec, dict):
                _model = _rec.get("model") or _rec.get("params", {}).get("model")
            _prompt = (
                locals().get("messages", None)
                or getattr(_rec, "prompt", None)
                or (isinstance(_rec, dict) and _rec.get("prompt"))
            )
            # Output: prefer the just-produced response variable from your method
            _output = (
                locals().get("response")
                or locals().get("scratchpad")
                or (isinstance(_rec, dict) and _rec.get("output"))
            )
            _usage = _rec.get("usage") if isinstance(_rec, dict) else None
            _run_id = _rec.get("run_id") if isinstance(_rec, dict) else None

            if os.getenv("AEGIS_TRACE_GENERATIONS", "1") != "0":
                log_generation(
                    run_id=_run_id,
                    model=_model,
                    prompt=_prompt,
                    output=_output,
                    usage=_usage,
                    meta={"provider": "replay"},
                )
        except Exception:
            pass

    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        runtime_config: RuntimeExecutionConfig,
        raw_response: bool = False,
    ) -> Union[str, Any]:
        raise NotImplementedError("ReplayProvider does not support get_completion.")

    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError("ReplayProvider does not support get_speech.")

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("ReplayProvider does not support get_transcription.")

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("ReplayProvider does not support ingest_document.")

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("ReplayProvider does not support retrieve_knowledge.")
