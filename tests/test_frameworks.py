"""The framework layer: settings, typed critic output, semantic index, orchestration graphs, judgment evaluation, DuckDB lookup.
No model calls: everything below runs without keys."""
import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_settings_reads_env_and_derives_provider(monkeypatch):
    from helix.settings import Settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x"); monkeypatch.setenv("LLM_PROVIDER", "")
    assert Settings(_env_file=None).provider() == "anthropic"
    monkeypatch.delenv("ANTHROPIC_API_KEY"); monkeypatch.setenv("WANDB_API_KEY", "y")
    assert Settings(_env_file=None).provider() == "wandb"
    monkeypatch.setenv("LLM_PROVIDER", "litellm")
    assert Settings(_env_file=None).provider() == "litellm"


def test_verdict_schema_rejects_bad_labels():
    from pydantic import ValidationError
    from helix.critic import Verdict
    assert Verdict(label="contradicted", confidence=0.9, reason="padj 0.23").label == "contradicted"
    with pytest.raises(ValidationError):
        Verdict(label="park", confidence=0.5, reason="x")
    with pytest.raises(ValidationError):
        Verdict(label="ok", confidence=1.5, reason="x")


def test_critic_uses_typed_output_then_falls_back(monkeypatch):
    from helix import critic as Cmod, llm
    calls = []
    monkeypatch.setattr(llm, "chat_typed", lambda system, user, schema, **kw: calls.append("typed") or schema(label="underpowered", confidence=0.7, reason="mean count 8"))
    c = Cmod.Critic(model="fake")
    assert c.judge({"input": {"table_facts": {}, "next_step": "x"}})["label"] == "underpowered" and calls == ["typed"]
    monkeypatch.setattr(llm, "chat_typed", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no structured mode")))
    monkeypatch.setattr(llm, "chat", lambda *a, **k: 'prose then {"label": "confound", "confidence": 0.8, "reason": "carriers 2/6"}')
    assert c.judge({"input": {"table_facts": {}, "next_step": "x"}})["label"] == "confound"


def test_parse_typed_finds_first_valid_object():
    from helix.llm import parse_typed
    from helix.critic import Verdict
    v = parse_typed('{"label": "nope"} ... {"label": "ok", "confidence": 0.5, "reason": "fine"}', Verdict)
    assert v.label == "ok"


def test_semantic_index_ranks_by_meaning(tmp_path, monkeypatch):
    pytest.importorskip("model2vec")
    from helix.graph import index as I
    monkeypatch.setattr(I, "DIR", str(tmp_path))
    ps = [{"id": "a", "text": "Reduced expression of cell cycle-regulating genes in the thymus after spaceflight."},
          {"id": "b", "text": "The soil moisture sensor was calibrated before each measurement."},
          {"id": "c", "text": "Bone mineral density decreased in hindlimb unloaded mice."}]
    idx = I.Index.build(ps, progress=lambda m: None)
    top = idx.search("E2f7 expression is reduced in spaceflight thymus; a cell cycle regulator", k=3)
    assert ps[top[0][0]]["id"] == "a"


def test_product_graph_routes_to_verify_when_judged(monkeypatch):
    from helix import orchestrate as O
    assert O.p_route({"judged": [1]}) == "verify" and O.p_route({}) == "summarize"
    g = O.product_graph().compile()
    names = set(g.get_graph().nodes)
    assert {"start", "summarize", "propose", "attach", "judge", "verify", "link"} <= names


def test_round_graph_fans_out_to_every_architect():
    from helix import orchestrate as O
    from helix.settings import settings
    g = O.round_graph().compile().get_graph()
    arch = [n for n in g.nodes if n.startswith("architect_")]
    assert len(arch) == len(settings.architects()) + 1            # model architects + ARIA
    edges = {(e.source, e.target) for e in g.edges}
    assert all(("judge", a) in edges and (a, "tournament") in edges for a in arch)
    assert ("tournament", "approval") in edges and ("approval", "promote") in edges


def test_tournament_needs_to_beat_current():
    from helix import orchestrate as O
    s = {"acc": 0.8, "candidates": [{"model": "a", "acc": 0.79}, {"model": "b", "acc": 0.75}]}
    assert O.r_tournament(s)["winner"] is None
    s["candidates"].append({"model": "c", "acc": 0.85})
    assert O.r_tournament(s)["winner"]["model"] == "c"


def test_judgment_evaluation_scores_against_labels():
    from helix.graph import evaluate as EV
    graph = {"nodes": [], "edges": [{"type": "finding-passage", "src": "f1", "dst": "p1", "relation": "supports", "p_supports": 0.9, "p_contradicts": 0.0}]}
    pairs = [{"finding_id": "f1", "passage_id": "p1", "relation": "supports", "labeller": "t"},
             {"finding_id": "f1", "passage_id": "p2", "relation": "unrelated", "labeller": "t"}]
    rows = EV.predictions(graph, pairs)
    assert [r["predicted"] for r in rows] == ["supports", "unrelated"]


def test_dspy_examples_load_labels():
    pytest.importorskip("dspy")
    from helix.dspy_baseline import examples, build_program
    exs = examples(os.path.join(ROOT, "data/golden/holdout.json"))
    assert len(exs) == 90 and all(e.label for e in exs)
    assert build_program() is not None


def test_duckdb_lookup_across_tables():
    pytest.importorskip("duckdb")
    from helix.tables import across_field
    rows = across_field(["Drd4"])
    assert any(r["dataset"] == "OSD-255" and r["direction"] == 1 for r in rows)
