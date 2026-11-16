import json

import pytest
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.sqlite import SqliteSaver
from test_graph import CONFIG, decide, setup

from harness.cli import main
from harness.graph import build_graph


def test_status_and_invalid_decision_do_not_advance_paused_run(tmp_path, capsys):
    run, model, builder, _ = setup(tmp_path)
    config = {**CONFIG, "configurable": {"thread_id": run.directory.name}}
    with SqliteSaver.from_conn_string(str(run.directory / "checkpoints.sqlite")) as saver:
        graph = build_graph(model=RunnableLambda(model.respond), run=run, checkpointer=saver,
                            build_runner=builder)
        pending = graph.invoke({}, config)
    assert main(["status", "--run", str(run.directory)]) == 0
    assert '"status": "waiting_for_human"' in capsys.readouterr().out
    decision = decide(pending).resume
    decision["reviewer"] = "   "
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision))
    with pytest.raises(SystemExit) as error:
        main(["resume", "--run", str(run.directory), "--decision", str(path)])
    assert error.value.code == 2
    with SqliteSaver.from_conn_string(str(run.directory / "checkpoints.sqlite")) as saver:
        graph = build_graph(model=RunnableLambda(model.respond), run=run, checkpointer=saver,
                            build_runner=builder)
        assert graph.get_state(config).next == ("review_testcases",)
    assert not (run.directory / "hitl_decisions.json").exists()
