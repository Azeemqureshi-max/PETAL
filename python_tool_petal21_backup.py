import ast
import re

from shared_llm import generate


# =========================================================
# CODE CLEANING
# =========================================================

def clean_code(response):
    response = response.strip()

    match = re.search(
        r"```(?:python|py)?\s*\n?(.*?)```",
        response,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1).strip()

    lines = response.splitlines()

    code_starts = (
        "def ",
        "class ",
        "import ",
        "from ",
        "#",
        "with ",
        "if __name__",
    )

    for i, line in enumerate(lines):
        if line.strip().startswith(code_starts):
            return "\n".join(lines[i:]).strip()

    return response


# =========================================================
# SYNTAX CHECK
# =========================================================

def check_syntax(code):
    try:
        tree = ast.parse(code)
        return True, None, tree
    except SyntaxError as error:
        return False, str(error), None


# =========================================================
# SAFETY CHECK
# =========================================================

BLOCKED_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "input",
    "breakpoint",
}

BLOCKED_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "pathlib",
}


def safe_code_check(tree):

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                if node.func.id in BLOCKED_NAMES:
                    return False, f"Blocked function: {node.func.id}"

        if isinstance(node, ast.Import):

            for alias in node.names:

                module = alias.name.split(".")[0]

                if module in BLOCKED_MODULES:
                    return False, f"Blocked module: {module}"

                return False, (
                    f"Imports are not allowed in safe test mode: {module}"
                )

        if isinstance(node, ast.ImportFrom):

            module = (node.module or "").split(".")[0]

            if module in BLOCKED_MODULES:
                return False, f"Blocked module: {module}"

            return False, "Imports are not allowed in safe test mode."

        if isinstance(node, ast.Attribute):

            if node.attr.startswith("__"):
                return False, "Dunder attribute access is blocked."

    return True, None


# =========================================================
# SAFE EXECUTION
# =========================================================

def safe_print(*args, **kwargs):

    if "file" in kwargs:
        raise RuntimeError(
            "Writing directly to files is not allowed."
        )

    print(*args, **kwargs)


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "print": safe_print,
}


def safe_execute(code):

    valid, error, tree = check_syntax(code)

    if not valid:
        return False, f"Syntax error: {error}"

    safe, error = safe_code_check(tree)

    if not safe:
        return False, f"Safety blocked: {error}"

    environment = {
        "__builtins__": SAFE_BUILTINS
    }

    try:

        exec(
            compile(tree, "<petal_test>", "exec"),
            environment,
            environment
        )

        return True, "Safe execution completed."

    except Exception as error:

        return False, f"Runtime error: {error}"


# =========================================================
# PYTHON GENERATION
# =========================================================

def generate_python(request):

    messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's Python coding engine. "
                "Generate correct, complete Python code. "
                "Keep the code simple and readable. "
                "Return Python code only."
            )
        },
        {
            "role": "user",
            "content": request
        }
    ]

    response = generate(
        messages,
        max_new_tokens=300,
        temperature=0.2
    )

    code = clean_code(response)

    valid, syntax_error, tree = check_syntax(code)

    safety_error = None

    if valid:

        safe, safety_error = safe_code_check(tree)

        if safe:
            return code

    problem = syntax_error or safety_error

    repair_messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's Python repair engine. "
                "Fix the supplied Python code. "
                "Return only corrected Python code. "
                "Do not use imports, operating-system commands, "
                "file access, subprocesses, eval, or exec."
            )
        },
        {
            "role": "user",
            "content": (
                f"Request:\n{request}\n\n"
                f"Code:\n{code}\n\n"
                f"Problem:\n{problem}"
            )
        }
    ]

    repaired = generate(
        repair_messages,
        max_new_tokens=300,
        temperature=0.1
    )

    repaired_code = clean_code(repaired)

    valid, syntax_error, tree = check_syntax(repaired_code)

    if not valid:
        return (
            "# Petal could not generate valid Python code.\n"
            f"# Problem: {syntax_error}\n\n"
            + repaired_code
        )

    safe, safety_error = safe_code_check(tree)

    if not safe:
        return (
            "# Petal generated Python code, but the safety check blocked it.\n"
            f"# Reason: {safety_error}\n\n"
            + repaired_code
        )

    return repaired_code

    messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's Python coding engine. "
                "Generate correct, complete Python code. "
                "Keep the code simple and readable. "
                "Return Python code only."
            )
        },
        {
            "role": "user",
            "content": request
        }
    ]

    response = generate(
        messages,
        max_new_tokens=300,
        temperature=0.2
    )

    code = clean_code(response)

    valid, error, tree = check_syntax(code)

    if valid:

        safe, safe_error = safe_code_check(tree)

        if safe:
            return code

    else:
        safety_error = None

    repair_messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's Python repair engine. "
                "Fix the supplied Python code. "
                "Return only corrected Python code. "
                "Do not use imports, operating-system commands, "
                "file access, subprocesses, eval, or exec."
            )
        },
        {
            "role": "user",
            "content": (
                f"Request:\n{request}\n\n"
                f"Code:\n{code}\n\n"
                f"Problem:\n{error or safety_error}"
            )
        }
    ]

    repaired = generate(
        repair_messages,
        max_new_tokens=300,
        temperature=0.1
    )

    repaired_code = clean_code(repaired)

    valid, error, tree = check_syntax(repaired_code)

    if not valid:
        return (
            "# Petal could not generate valid Python code.\n"
            f"# Problem: {error}\n\n"
            + repaired_code
        )

    safe, safe_error = safe_code_check(tree)

    if not safe:
        return (
            "# Petal generated Python code, but the safety check blocked it.\n"
            f"# Reason: {safe_error}\n\n"
            + repaired_code
        )

    return repaired_code


# =========================================================
# TESTS
# =========================================================

if __name__ == "__main__":

    tests = [
        "Write Python code to calculate the average of a list.",
        "Write Python code to count words in a sentence.",
        "Write Python code to check if a number is prime.",
        "Write Python code to sort a list.",
        "Write Python code to read a text file."
    ]

    for request in tests:

        print()
        print("=" * 60)

        print("REQUEST:")
        print(request)

        code = generate_python(request)

        print()
        print("CODE:")
        print(code)

        valid, error, tree = check_syntax(code)

        if not valid:
            print()
            print("SYNTAX: INVALID")
            print(error)
            continue

        print()
        print("SYNTAX: VALID")

        safe, safe_error = safe_code_check(tree)

        if not safe:
            print("SAFETY: BLOCKED")
            print(safe_error)
            continue

        print("SAFETY: PASSED")

        success, result = safe_execute(code)

        if success:
            print("TEST: PASSED")
        else:
            print("TEST: FAILED")
            print(result)