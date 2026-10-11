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
#
# Petal is allowed to WRITE advanced Python.
#
# This checker is mainly for AUTOMATIC EXECUTION.
# It prevents generated code from directly performing
# destructive system actions or accessing sensitive data.
# =========================================================

BLOCKED_FUNCTIONS = {
    "exec",
    "eval",
    "compile",
    "__import__",
    "breakpoint",
}

BLOCKED_MODULES = {
    "os",
    "subprocess",
    "shutil",
    "ctypes",
    "winreg",
}

BLOCKED_IMPORT_PREFIXES = {
    "os",
    "subprocess",
    "shutil",
    "ctypes",
    "winreg",
}

BLOCKED_ATTRIBUTES = {
    "__globals__",
    "__code__",
    "__builtins__",
    "__subclasses__",
    "__mro__",
    "__bases__",
}


def is_blocked_module(module_name):

    if not module_name:
        return False

    root = module_name.split(".")[0]

    return root in BLOCKED_IMPORT_PREFIXES


def safe_code_check(tree):

    for node in ast.walk(tree):

        # -------------------------------------------------
        # Function calls
        # -------------------------------------------------

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                if node.func.id in BLOCKED_FUNCTIONS:

                    return (
                        False,
                        f"Blocked function: {node.func.id}"
                    )

        # -------------------------------------------------
        # Imports
        # -------------------------------------------------

        if isinstance(node, ast.Import):

            for alias in node.names:

                module = alias.name

                if is_blocked_module(module):

                    return (
                        False,
                        f"Blocked module: {module}"
                    )

        # -------------------------------------------------
        # From imports
        # -------------------------------------------------

        if isinstance(node, ast.ImportFrom):

            module = node.module or ""

            if is_blocked_module(module):

                return (
                    False,
                    f"Blocked module: {module}"
                )

        # -------------------------------------------------
        # Sensitive attributes
        # -------------------------------------------------

        if isinstance(node, ast.Attribute):

            if node.attr in BLOCKED_ATTRIBUTES:

                return (
                    False,
                    f"Blocked attribute: {node.attr}"
                )

    return True, None


# =========================================================
# SAFE PRINT
# =========================================================

def safe_print(*args, **kwargs):

    if "file" in kwargs:

        raise RuntimeError(
            "Direct file output is not allowed "
            "during automatic testing."
        )

    print(*args, **kwargs)


# =========================================================
# SAFE BUILTINS
# =========================================================
#
# Normal Python programming remains available.
# Dangerous dynamic execution functions are excluded.
# =========================================================

SAFE_BUILTINS = {

    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,

    "bytes": bytes,
    "bytearray": bytearray,

    "dict": dict,
    "enumerate": enumerate,

    "filter": filter,
    "float": float,

    "format": format,

    "frozenset": frozenset,

    "hash": hash,

    "int": int,

    "isinstance": isinstance,
    "issubclass": issubclass,

    "len": len,

    "list": list,

    "map": map,
    "max": max,
    "min": min,

    "object": object,

    "pow": pow,

    "print": safe_print,

    "range": range,
    "repr": repr,
    "reversed": reversed,

    "round": round,

    "set": set,
    "slice": slice,
    "sorted": sorted,

    "str": str,
    "sum": sum,

    "tuple": tuple,

    "type": type,

    "zip": zip,
}


# =========================================================
# SAFE EXECUTION
# =========================================================

def safe_execute(code):

    valid, error, tree = check_syntax(code)

    if not valid:

        return (
            False,
            f"Syntax error: {error}"
        )

    safe, error = safe_code_check(tree)

    if not safe:

        return (
            False,
            f"Safety blocked: {error}"
        )

    environment = {
        "__builtins__": SAFE_BUILTINS
    }

    try:

        exec(
            compile(
                tree,
                "<petal_test>",
                "exec"
            ),
            environment,
            environment
        )

        return (
            True,
            "Safe execution completed."
        )

    except Exception as error:

        return (
            False,
            f"Runtime error: {error}"
        )


# =========================================================
# PYTHON GENERATION
# =========================================================

def generate_python(request):

    messages = [

        {
            "role": "system",
            "content": (
                "You are Petal's Python coding engine. "
                "Generate correct, complete and useful Python code. "
                "You may write advanced Python when requested. "
                "Use appropriate standard-library modules when useful. "
                "Use external libraries when the user's request requires them. "
                "Prefer clean, maintainable and readable code. "
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
        max_new_tokens=500,
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

    # -----------------------------------------------------
    # Repair
    # -----------------------------------------------------

    repair_messages = [

        {
            "role": "system",
            "content": (
                "You are Petal's Python repair engine. "
                "Fix the supplied Python code. "
                "Return only corrected Python code. "
                "Do not use destructive system operations, "
                "subprocess execution, dynamic code execution, "
                "or access to private credentials."
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
        max_new_tokens=500,
        temperature=0.1
    )

    repaired_code = clean_code(repaired)

    valid, syntax_error, tree = check_syntax(
        repaired_code
    )

    if not valid:

        return (
            "# Petal could not generate valid Python code.\n"
            f"# Problem: {syntax_error}\n\n"
            + repaired_code
        )

    safe, safety_error = safe_code_check(tree)

    if not safe:

        return (
            "# Petal generated Python code, "
            "but automatic execution safety blocked it.\n"
            f"# Reason: {safety_error}\n\n"
            + repaired_code
        )

    return repaired_code


# =========================================================
# TESTS
# =========================================================

if __name__ == "__main__":

    tests = [

        "Write Python code to calculate "
        "the average of a list.",

        "Write Python code to count "
        "words in a sentence.",

        "Write Python code to check "
        "if a number is prime.",

        "Write Python code to sort "
        "a list.",

        "Write Python code using the "
        "math and random modules.",

        "Write Python code to read "
        "a text file."

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