import ast
from pathlib import Path


def test_online_migrations_end_role_check_transaction_before_alembic_transaction() -> (
    None
):
    env_file = Path(__file__).parents[1] / "migrations" / "env.py"
    tree = ast.parse(env_file.read_text(encoding="utf-8"))
    online_function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_migrations_online"
    )
    role_check = next(
        node
        for node in ast.walk(online_function)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "roles"
    )
    calls = {
        node.func.attr: node.lineno
        for node in ast.walk(online_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {"rollback", "configure", "begin_transaction", "run_migrations"}
    }

    assert role_check.lineno < calls["rollback"]
    assert calls["rollback"] < calls["configure"]
    assert calls["configure"] < calls["begin_transaction"]
    assert calls["begin_transaction"] < calls["run_migrations"]
