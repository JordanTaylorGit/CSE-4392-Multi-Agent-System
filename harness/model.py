"""Provider construction is confined to create_model; stages receive a client."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable


DEFAULT_MODEL = "qwen2.5-coder:14b"


def create_model():
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.environ.get("MODEL_NAME", DEFAULT_MODEL),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        temperature=0,
        format="json",
        num_ctx=32768,
        num_predict=12000,
        client_kwargs={"timeout": 600},
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
            json.dumps({"request": payload, "skill": skill, "response": text}, indent=2) + "\n",
            encoding="utf-8",
        )
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError(f"{stage}: model response must be a JSON object")
        return result
