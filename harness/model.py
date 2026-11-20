"""Provider construction is confined to create_model; stages receive a client."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

DEFAULT_MODEL = "groot"
DEFAULT_BASE_URL = "http://192.168.1.185:8080/v1"


def create_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("MODEL_NAME", DEFAULT_MODEL),
        base_url=os.environ.get("MODEL_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("MODEL_API_KEY", "local"),
        temperature=0,
        timeout=int(os.environ.get("MODEL_TIMEOUT", "1800")),
        max_tokens=int(os.environ.get("MODEL_MAX_TOKENS", "16384")),
        model_kwargs={"response_format": {"type": "json_object"}},
    )


class SkillClient:
    """Execute a stage prompt using any compatible LangChain runnable."""

    def __init__(self, model: Runnable, transcripts: Path):
        self.model = model
        self.transcripts = transcripts

    def request(self, stage: str, skill: str, task: str, context: dict) -> dict:
        payload = {"stage": stage, "task": task, "context": context}
        messages = [
            SystemMessage(content=(skill + "\n\nReturn one JSON object only. "
                                   "Do not claim to run commands, approve a human gate, or "
                                   "measure coverage. The runtime performs those actions.")),
            HumanMessage(content=json.dumps(payload)),
        ]
        response: BaseMessage = self.model.invoke(messages)
        text = response.text
        self.transcripts.mkdir(parents=True, exist_ok=True)
        (self.transcripts / f"{stage}-{uuid4().hex}.json").write_text(
            json.dumps({"request": payload, "skill": skill, "response": text,
                        "model": response.response_metadata.get("model", getattr(self.model, "model", type(self.model).__name__))},
                       indent=2) + "\n",
            encoding="utf-8",
        )
        result = json.loads(text)
        if not isinstance(result, dict):
            raise TypeError(f"{stage}: model response must be a JSON object")
        return result
