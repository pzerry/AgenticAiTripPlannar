from pathlib import Path

PROMPT_DIR = Path(__file__).parent.parent / "Prompts" / "system"


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts/system directory."""
    with open(PROMPT_DIR / filename, "r", encoding="utf-8") as file:
        return file.read()