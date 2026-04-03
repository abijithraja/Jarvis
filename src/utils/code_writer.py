def write_code_to_file(code, filename="output.py"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    return f"Code written to {filename}"
