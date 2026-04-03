import os


def write_code_to_file(code: str, filename: str = "output.py", directory: str | None = None) -> str:
    """Write generated code to a file, stripping markdown fences if present."""
    # Strip ```python ... ``` fences that LLMs often add
    if "```" in code:
        lines = code.split("\n")
        cleaned = []
        inside = False
        for line in lines:
            if line.strip().startswith("```"):
                inside = not inside
                continue
            if inside or not any(line.startswith("```") for _ in [1]):
                cleaned.append(line)
        code = "\n".join(cleaned)

    out_path = os.path.join(directory, filename) if directory else filename
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code.strip())

    abs_path = os.path.abspath(out_path)
    return f"Code saved to {abs_path}"
