"""Log one iteration to W&B following the contract ARIA recommended.

    log_iteration(n, result, rules_path, config)   # result = evaluate(...) output

One run per iteration, job_type "critic-iteration"; metrics under screening/ and reason/;
per-hypothesis table at evaluation/hypotheses; rules consumed and produced as the
versioned artifact "critic-rules". No-op (prints) if wandb is not installed or no key.
"""
import os


def log_iteration(n, result, rules_path, config, project=None, prev_rules_path=None, group="helix-osd104"):
    try:
        import wandb
        assert os.getenv("WANDB_API_KEY"), "no WANDB_API_KEY"
    except Exception as e:
        print(f"[wandb off: {e}] iter {n}: " + ", ".join(
            f"{k.split('/')[1]}={v:.2f}" for k, v in result["metrics"].items()
            if k.startswith("screening/") and isinstance(v, float)))
        return None
    run = wandb.init(project=project or os.getenv("WANDB_PROJECT", "helix"), group=group,
                     job_type="critic-iteration", name=f"iter-{n:03d}-rules-v{n}",
                     config={"iteration": n, "critic/rules_file": os.path.basename(rules_path), **config})
    if prev_rules_path:                                   # lineage: this run consumed the previous rules
        run.use_artifact(f"critic-rules:iteration-{n-1:03d}") if n > 0 else None
    run.log({k: v for k, v in result["metrics"].items() if v is not None})
    cols = list(result["rows"][0].keys()) if result["rows"] else []
    run.log({"evaluation/hypotheses": wandb.Table(columns=cols, data=[[r[c] for c in cols] for r in result["rows"]])})
    art = wandb.Artifact("critic-rules", type="critic-rules",
                         metadata={"iteration": n, "author": config.get("architect", "human")})
    art.add_file(rules_path, name="rules.md")
    run.log_artifact(art, aliases=[f"iteration-{n:03d}", "candidate"])
    run.finish()
    return run.id
