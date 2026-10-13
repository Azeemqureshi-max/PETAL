
import ast
import operator
import re


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def _prepare(expression):
    expression = expression.strip().replace("^", "**")
    expression = re.sub(r"(?<=\d)(?=x\b)", "*", expression)
    return expression


def _parse(expression):
    return ast.parse(_prepare(expression), mode="eval").body


def calculate(expression):
    tree = _parse(expression)

    def evaluate(node):
        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return node.value
            raise ValueError("Only numbers are allowed.")

        if isinstance(node, ast.BinOp):
            operation = OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported operator.")

            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent is too large.")

            if isinstance(node.op, ast.Div) and right == 0:
                raise ZeroDivisionError("Cannot divide by zero.")

            result = operation(left, right)

            if isinstance(result, complex) or abs(result) > 1e100:
                raise ValueError("Result is outside the supported range.")

            return result

        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value

        raise ValueError("Unsupported expression.")

    return evaluate(tree)


def _linear(expression):
    tree = _parse(expression)

    # Represent each expression as (coefficient of x, constant).
    def evaluate(node):
        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return (0, node.value)
            raise ValueError("Only numbers are allowed.")

        if isinstance(node, ast.Name) and node.id == "x":
            return (1, 0)

        if isinstance(node, ast.UnaryOp):
            a, b = evaluate(node.operand)
            if isinstance(node.op, ast.USub):
                return (-a, -b)
            if isinstance(node.op, ast.UAdd):
                return (a, b)

        if isinstance(node, ast.BinOp):
            a, b = evaluate(node.left)
            c, d = evaluate(node.right)

            if isinstance(node.op, ast.Add):
                return (a + c, b + d)

            if isinstance(node.op, ast.Sub):
                return (a - c, b - d)

            if isinstance(node.op, ast.Mult):
                if a != 0 and c != 0:
                    raise ValueError("This solver only supports linear equations.")
                return (a * d + c * b, b * d)

            if isinstance(node.op, ast.Div):
                if c != 0:
                    raise ValueError("Division by an expression containing x is unsupported.")
                if d == 0:
                    raise ZeroDivisionError("Cannot divide by zero.")
                return (a / d, b / d)

            if isinstance(node.op, ast.Pow):
                if c != 0:
                    raise ValueError("The exponent must be a number.")
                if d == 1:
                    return (a, b)
                if a != 0:
                    raise ValueError("This solver only supports linear equations.")
                return (0, b ** d)

        raise ValueError("Unsupported equation expression.")

    return evaluate(tree)


def solve_equation(equation):
    if equation.count("=") != 1:
        raise ValueError("Please enter one equation with one equals sign.")

    left, right = equation.split("=", 1)
    a, b = _linear(left)
    c, d = _linear(right)

    coefficient = a - c
    constant = d - b

    if coefficient == 0:
        if constant == 0:
            return "This equation has infinitely many solutions."
        return "This equation has no solution."

    answer = constant / coefficient

    if not (-1e100 < answer < 1e100):
        raise ValueError("The solution is outside the supported range.")

    return f"x = {answer:.10g}"


if __name__ == "__main__":
    for expression in ["25 + 17", "7 * 8", "100 / 4", "2 ^ 10", "50 - 23"]:
        print(f"{expression} = {calculate(expression)}")

    for equation in ["2*x + 5 = 15", "3x - 6 = 12", "x/2 = 8"]:
        print(f"{equation} -> {solve_equation(equation)}")