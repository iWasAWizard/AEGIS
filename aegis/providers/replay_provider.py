# aegis/providers/replay_provider.py
"""
A mock BackendProvider for replaying agent tasks from a log.
"""
from typing import List, Dict, Any, Optional, Type, Union

from pydantic import BaseModel

from aegis.exceptions import PlannerError
from aegis.providers.base import BackendProvider
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


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
