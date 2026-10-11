import os


# =========================================================
# PETAL SAFE FILE AREA
# =========================================================

SAFE_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "user_files"
    )
)


os.makedirs(SAFE_ROOT, exist_ok=True)


# =========================================================
# PATH SAFETY
# =========================================================

def safe_path(filename):

    filename = filename.strip()

    if not filename:
        raise ValueError("Filename cannot be empty.")

    path = os.path.abspath(
        os.path.join(SAFE_ROOT, filename)
    )

    # Make sure the final path stays inside SAFE_ROOT.
    if os.path.commonpath([SAFE_ROOT, path]) != SAFE_ROOT:
        raise ValueError(
            "Access denied: file must stay inside Petal's safe file area."
        )

    return path


# =========================================================
# READ FILE
# =========================================================

def read_file(filename):

    try:
        path = safe_path(filename)

        if not os.path.exists(path):
            return f"File not found: {filename}"

        if not os.path.isfile(path):
            return f"Not a file: {filename}"

        with open(path, "r", encoding="utf-8") as file:
            content = file.read()

        return content

    except Exception as error:
        return f"File read error: {error}"


# =========================================================
# WRITE FILE
# =========================================================

def write_file(filename, content):

    try:
        path = safe_path(filename)

        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

        return f"File written successfully: {filename}"

    except Exception as error:
        return f"File write error: {error}"


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_filename = "petal_test.txt"

    print("Writing test file...")

    result = write_file(
        test_filename,
        "Hello from Petal."
    )

    print(result)

    print()
    print("Reading test file...")

    result = read_file(test_filename)

    print(result)