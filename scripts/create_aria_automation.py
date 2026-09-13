"""Create (or replace) the W&B Automation that sends ARIA the analyst prompt when a critic
iteration finishes (metric screening/eval_complete >= 1 on any run in the project).

    python3 scripts/create_aria_automation.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import wandb
from wandb.automations import OnRunMetric, RunEvent, SendPromptToAria

load_dotenv(".env")
NAME = "helix-aria-analyst"


def main():
    api = wandb.Api(api_key=os.environ["WANDB_API_KEY"])
    project = api.project(os.getenv("WANDB_PROJECT", "Helix"), entity=os.environ["WANDB_ENTITY"])
    for a in api.automations(entity=os.environ["WANDB_ENTITY"]):
        if a.name == NAME:
            api.delete_automation(a); print("replaced existing", NAME)
    text = open("kit/aria_automation_prompt.md").read()
    prompt = text.split("## Automation prompt (paste into the Trigger ARIA action)")[1].split("## Demo flow")[0].strip()
    event = OnRunMetric(scope=project, filter=RunEvent.metric("screening/eval_complete") >= 1)
    auto = api.create_automation(event >> SendPromptToAria(prompt=prompt), name=NAME,
                                 description="Critic iteration finished: ask ARIA to diagnose misses and propose a rules patch.")
    print("created", auto.name, "enabled:", auto.enabled)


if __name__ == "__main__":
    main()
