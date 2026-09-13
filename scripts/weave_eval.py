"""Entry point for helix.weave_eval (see that module's docstring for usage)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helix.weave_eval import cli

if __name__ == "__main__":
    cli()
