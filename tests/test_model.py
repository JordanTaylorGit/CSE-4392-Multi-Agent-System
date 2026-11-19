import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from harness.model import SkillClient, create_model


def test_default_and_replacement_model_are_selected_only_at_construction(monkeypatch):
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = create_model()
    assert default.model == "qwen3-coder:30b"
    assert default.base_url == "http://127.0.0.1:11434"
    monkeypatch.setenv("MODEL_NAME", "another-model")
    assert create_model().model == "another-model"


def test_injected_models_need_no_api_key_and_receive_skill_and_context(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    messages_seen = []

    def respond(messages):
        messages_seen.extend(messages)
        return AIMessage(content='{"answer": 42}')

    client = SkillClient(RunnableLambda(respond), tmp_path)
    result = client.request("example", "Skill instructions", "Do the task", {"source": "code"})
    assert result == {"answer": 42}
    assert "Skill instructions" in messages_seen[0].content
    assert json.loads(messages_seen[1].content)["context"] == {"source": "code"}
    assert list(tmp_path.glob("*.json"))


@pytest.mark.parametrize("answer", ["", "not JSON", "[]"])
def test_invalid_model_responses_fail_instead_of_becoming_artifacts(tmp_path, answer):
    client = SkillClient(RunnableLambda(lambda _: AIMessage(content=answer)), tmp_path)
    with pytest.raises((ValueError, TypeError)):
        client.request("example", "Skill", "Task", {})
