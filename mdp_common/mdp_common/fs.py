from re import sub, IGNORECASE


def make_path_compatible(input: str) -> str:
    return sub("[^A-Z0-9_]", "_", input, flags=IGNORECASE)