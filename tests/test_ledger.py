from helix.ledger import Ledger
from helix.schema import CriticVerdict, Evidence, Lead, Verdict


def test_roundtrip_and_queries(tmp_path):
    ledger = Ledger(tmp_path / "leads.jsonl")
    alloc = ledger.id_allocator()
    assert alloc() == "lead_0001"
    assert alloc() == "lead_0002"
    lead = Lead(
        id="lead_0001", iteration=1, claim="c", confidence=0.5, why_not_known="w", next_step="n",
        evidence=[Evidence(source="s")], trace="t",
        critic=CriticVerdict(verdict=Verdict.KILL, score=0.1, reasons=["restates textbook result"]),
    )
    ledger.append(lead)
    assert ledger.id_allocator()() == "lead_0002"
    assert ledger.claims() == ["c"]
    assert len(ledger.killed()) == 1
    assert ledger.survivors() == []
    assert ledger.by_iteration(1)[0].id == "lead_0001"
