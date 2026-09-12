import pytest
from pydantic import ValidationError

from helix.schema import CriticVerdict, Evidence, Lead, Verdict


def _lead(**overrides):
    base = dict(
        id="lead_0001", iteration=1, claim="X co-occurs with Y in Z under T",
        evidence=[Evidence(source="GEO:GSE1", artifact="table_de", rows=["X"])],
        confidence=0.6, why_not_known="reviews cover Y generally", next_step="recompute with batch covariate",
        trace="weave://local/scout/abc",
    )
    base.update(overrides)
    return Lead(**base)


def test_lead_requires_evidence():
    with pytest.raises(ValidationError):
        _lead(evidence=[])


def test_lead_requires_trace():
    with pytest.raises(ValidationError):
        Lead(**{k: v for k, v in _lead().model_dump().items() if k != "trace"})


def test_survived_property():
    l = _lead()
    assert not l.survived
    l.critic = CriticVerdict(verdict=Verdict.SURVIVE, score=0.8)
    assert l.survived
    l.critic = CriticVerdict(verdict=Verdict.PARK, score=0.3)
    assert not l.survived
