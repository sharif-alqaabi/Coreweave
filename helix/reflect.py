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


def apply_patch(rules_path, patch_text, change_reason="", author="aria"):
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
    n = int(re.search(r"v(\d+)", os.path.basename(rules_path)).group(1)) + 1
    out = os.path.join(os.path.dirname(rules_path), f"rules_v{n}.md")
    open(out, "w").write(text)
    json.dump({"iteration": n, "parent": os.path.basename(rules_path), "author": author,
               "change_reason": change_reason, "sections": list(changes)},
              open(out.replace(".md", ".meta.json"), "w"), indent=1)
    return out


def propose_patch_claude(misses, rules_path, model=None):
    """Fallback architect. Returns patch text in the same format ARIA is asked for."""
    import anthropic
    prompt = (f"Current critic rules:\n\n{open(rules_path).read()}\n\n"
              f"Misses this iteration (critic label vs human label):\n{json.dumps(misses, indent=1)[:6000]}\n\n"
              f"Rewrite at most {MAX_SECTIONS} sections so the critic would get these right without "
              "breaking correct cases. Output ONLY the changed sections, each as '## <name>' followed by "
              "the full replacement text. Cite the hypothesis_ids each change fixes inside the text.")
    msg = anthropic.Anthropic().messages.create(model=model or os.getenv("ARCHITECT_MODEL", "claude-opus-5"),
                                                max_tokens=1200, messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text
