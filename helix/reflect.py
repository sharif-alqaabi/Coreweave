"""The architect step: turn misses into the next rules version.

    apply_patch("kit/critic/rules_v0.md", patch_text)   -> writes rules_v1.md, returns path
    propose_patch_claude(misses, rules_path)             -> patch_text (fallback when no ARIA patch)

A patch is plain text with one or more blocks:

    ## confound
    <full replacement text for that section>

Guardrails: at most MAX_SECTIONS sections change per version; the file may not exceed
MAX_WORDS; unknown section names are rejected. Every version stays on disk.
"""
import json, os, re
from helix.critic_payload import OPTIONS

MAX_SECTIONS, MAX_WORDS = 2, 450


def _sections(text):
    """Split a rules file into {"_head": ..., "ok": ..., "confound": ...} preserving order."""
    parts = re.split(r"^## (\w+)\s*$", text, flags=re.M)
    out = {"_head": parts[0].rstrip()}
    for name, body in zip(parts[1::2], parts[2::2]):
        out[name] = body.strip()
    return out


def render_patch(rules_path, patch_text):
    """Validate a patch against a rules file and return the merged text. Raises ValueError."""
    cur = _sections(open(rules_path).read())
    new = _sections("\n" + patch_text)                    # leading newline so first "## x" splits
    changes = {k: v for k, v in new.items() if k != "_head"}
    bad = [k for k in changes if k not in OPTIONS]
    if bad:
        raise ValueError(f"patch names unknown sections: {bad}")
    if len(changes) > MAX_SECTIONS:
        raise ValueError(f"patch changes {len(changes)} sections; max is {MAX_SECTIONS}")
    merged = {**cur, **changes}
    text = merged["_head"] + "\n\n" + "\n\n".join(f"## {k}\n{merged[k]}" for k in merged if k != "_head") + "\n"
    if len(text.split()) > MAX_WORDS:
        raise ValueError(f"rules would be {len(text.split())} words; max is {MAX_WORDS}")
    return text, list(changes)


def apply_patch(rules_path, patch_text, change_reason="", author="aria", extra_meta=None, out_version=None):
    """Validate, then write rules_v{out_version}.md (default: base+1) atomically. Returns the new path.
    out_version matters after a rollback: base may be v2 while the next iteration needs v4."""
    text, changed = render_patch(rules_path, patch_text)
    n = out_version if out_version is not None else int(re.search(r"v(\d+)", os.path.basename(rules_path)).group(1)) + 1
    out = os.path.join(os.path.dirname(rules_path), f"rules_v{n}.md")
    if os.path.exists(out):
        raise ValueError(f"{out} already exists; refusing to overwrite")
    tmp = out + ".tmp"
    open(tmp, "w").write(text); os.replace(tmp, out)              # atomic on POSIX
    json.dump({"version": n, "parent": os.path.basename(rules_path), "author": author,
               "change_reason": change_reason, "sections": changed, **(extra_meta or {})},
              open(out.replace(".md", ".meta.json"), "w"), indent=1)
    return out


try:
    import weave
    traced = weave.op()
except Exception:                                   # weave missing: plain functions
    def traced(fn): return fn


@traced
def propose_patch_claude(misses, rules_path, model=None, feedback=""):
    """Fallback architect. Returns patch text in the same format ARIA is asked for."""
    from helix import llm
    words = len(open(rules_path).read().split())
    direction = "\n".join(f"- {m['hypothesis_id']}: critic said `{m['critic_reason_code']}`, human says `{m['human_reason_code']}` "
                          f"-> the rules must make the critic output `{m['human_reason_code']}`. Claim: {m['hypothesis_text'][:120]}"
                          for m in misses)
    prompt = (f"Current critic rules ({words} words; hard cap {MAX_WORDS} words total):\n\n{open(rules_path).read()}\n\n"
              f"Misses this iteration. For each, the REQUIRED output is the human label:\n{direction}\n\n"
              f"Details:\n{json.dumps(misses, indent=1)[:5000]}\n\n"
              "The human labels are ground truth. Never add exceptions that let the critic keep its current answer. "
              "Pick the section named by the most common REQUIRED label and make it catch those leads "
              f"(e.g. if humans say already_known, broaden `## already_known`). Rewrite at most {MAX_SECTIONS} sections. "
              "Keep each rewritten section under 70 words; the whole file must stay under the cap, so tighten "
              "wording rather than adding sentences. Output ONLY the changed sections, each as '## <name>' "
              "followed by the full replacement text, citing the hypothesis_ids it fixes." + (f"\n\n{feedback}" if feedback else ""))
    return llm.chat("You are the architect of a scientific critic. Output only the requested sections.",
                    prompt, model=model or os.getenv("ARCHITECT_MODEL"), max_tokens=1200)
