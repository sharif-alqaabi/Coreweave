"""Read a rules patch that ARIA wrote back to W&B for a given iteration run.

ARIA cannot call our code, but it can run Python inside W&B. The automation prompt asks it to
write its proposed patch to the iteration's run in ONE of three places; we accept any:
  1. run.summary["aria/patch"]        (string with '## section' blocks)
  2. run.notes                        (same text)
  3. an artifact named aria-patch-iter{n}, type aria-patch, containing patch.md

fetch_aria_patch(run_id, n, timeout_s) polls until found or timeout. Returns text or None.
"""
import os, re, time

SECTION = re.compile(r"^## \w+", re.M)


def _looks_like_patch(text):
    return bool(text) and bool(SECTION.search(text))


def fetch_aria_patch(run_id, n, timeout_s=120, poll_s=10, project=None, entity=None):
    import wandb
    api = wandb.Api(api_key=os.environ["WANDB_API_KEY"])
    path = f"{entity or os.environ['WANDB_ENTITY']}/{project or os.getenv('WANDB_PROJECT', 'Helix')}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            run = api.run(f"{path}/{run_id}")
            run.load(force=True)                       # Api caches run objects; without this every poll re-reads the first, stale summary
            for text in (run.summary.get("aria/patch"), run.notes):
                if _looks_like_patch(text):
                    return text
            for art in run.logged_artifacts():
                if art.type == "aria-patch":
                    d = art.download(root=f"results/_aria/{art.name}")
                    for f in os.listdir(d):
                        text = open(os.path.join(d, f)).read()
                        if _looks_like_patch(text):
                            return text
            try:                                                   # artifact logged by ARIA's own script
                art = api.artifact(f"{path}/aria-patch-iter{n}:latest")
                d = art.download(root=f"results/_aria/iter{n}")
                for f in os.listdir(d):
                    text = open(os.path.join(d, f)).read()
                    if _looks_like_patch(text):
                        return text
            except Exception:
                pass
        except Exception as e:
            print(f"  aria channel: {str(e)[:80]}")
        time.sleep(poll_s)
    return None
