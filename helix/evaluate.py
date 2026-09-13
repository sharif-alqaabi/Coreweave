"""Score critic verdicts against human labels.

    result = evaluate(verdicts, leads)     # leads carry "label" (human) after split_golden

Returns metrics named to ARIA's logging contract, plus `misses` for the architect
and `rows` for the per-hypothesis W&B table. "kill" = any label other than "ok".
"""
from collections import Counter, defaultdict
from helix.critic_payload import OPTIONS


def evaluate(verdicts, leads, threshold=0.0):
    human = {l["id"]: l for l in leads}
    rows, misses = [], []
    tp = fp = fn = tn = correct = 0
    conf = Counter()                                     # (human_label, critic_label) -> n
    for v in verdicts:
        lead = human[v["lead_id"]]
        h, c = lead["label"], v["label"]
        c_kill = c != "ok" and v["confidence"] >= threshold
        h_kill = h != "ok"
        tp += c_kill and h_kill; fp += c_kill and not h_kill
        fn += (not c_kill) and h_kill; tn += (not c_kill) and not h_kill
        correct += h == c
        conf[(h, c)] += 1
        row = {"hypothesis_id": v["lead_id"], "hypothesis_text": lead["claim"], "shape": lead.get("shape"),
               "critic_verdict": "kill" if c_kill else "keep", "critic_reason_code": c,
               "critic_confidence": v["confidence"], "critic_reason": v["reason"],
               "human_verdict": "kill" if h_kill else "keep", "human_reason_code": h,
               "human_note": lead.get("label_note", ""), "is_correct": h == c,
               "is_false_kill": bool(c_kill and not h_kill), "rules_version": v["rules_version"],
               "table_facts": str(lead.get("table_facts", ""))[:500]}
        rows.append(row)
        if h != c:
            misses.append(row)
    per_reason = {}
    for code in OPTIONS:
        pred = sum(n for (hh, cc), n in conf.items() if cc == code)
        true = sum(n for (hh, cc), n in conf.items() if hh == code)
        hit = conf[(code, code)]
        per_reason[code] = {"precision": hit / pred if pred else None,
                            "recall": hit / true if true else None, "support": true}
    n = len(verdicts)
    metrics = {"screening/kill_precision": tp / (tp + fp) if tp + fp else None,
               "screening/kill_recall": tp / (tp + fn) if tp + fn else None,
               "screening/false_kill_rate": fp / (fp + tn) if fp + tn else None,
               "screening/reason_accuracy": correct / n if n else None,
               "screening/n_hypotheses": n, "screening/false_kills": fp,
               "screening/true_kills": tp, "screening/predicted_kills": tp + fp,
               "screening/n_human_kill": tp + fn, "screening/mean_confidence": sum(v["confidence"] for v in verdicts) / n if n else None}
    for code, m in per_reason.items():
        for k, val in m.items():
            metrics[f"reason/{code}/{k}"] = val
    return {"metrics": metrics, "confusion": dict(conf), "misses": misses, "rows": rows}
