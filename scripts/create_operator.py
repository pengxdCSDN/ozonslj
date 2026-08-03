"""通过服务器命令创建或更新运营账号，不提供公网注册入口。"""

import argparse
import getpass
import sys
from pathlib import Path
from uuid import uuid4

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.application.identity import PasswordHasher  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.domain.identity import OperatorRole  # noqa: E402
from backend.app.infrastructure.postgres.migrations import migrate_postgres  # noqa: E402

ROLES: tuple[OperatorRole, ...] = (
    "admin",
    "supervisor",
    "operator",
    "finance",
    "readonly_analyst",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="创建或更新 ozonslj 运营账号")
    parser.add_argument("--email", required=True, help="登录邮箱")
    parser.add_argument("--display-name", required=True, help="显示名称")
    parser.add_argument("--role", choices=ROLES, default="admin", help="组织级角色")
    parser.add_argument(
        "--workspace",
        action="append",
        default=[],
        help="授权工作区 ID，可重复；admin 未指定时授权全部启用工作区",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    if email.count("@") != 1:
        raise SystemExit("邮箱格式不正确")
    password = getpass.getpass("密码（至少 12 位）: ")
    confirmation = getpass.getpass("再次输入密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")
    if len(password) < 12:
        raise SystemExit("密码至少需要 12 位")

    settings = Settings()
    dsn = settings.postgres_dsn()
    migrate_postgres(dsn)
    password_hash = PasswordHasher().hash(password)

    with psycopg.connect(dsn) as connection, connection.transaction():
        operator_id = _upsert_operator(
            connection,
            email=email,
            display_name=args.display_name.strip(),
            role=args.role,
            password_hash=password_hash,
        )
        workspace_ids = list(dict.fromkeys(args.workspace))
        if args.role == "admin" and not workspace_ids:
            workspace_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM store_workspaces WHERE is_active ORDER BY id"
                ).fetchall()
            ]
        _replace_memberships(connection, operator_id, workspace_ids)

    print(f"账号已保存：{email}，角色：{args.role}，工作区数量：{len(workspace_ids)}")


def _upsert_operator(
    connection: psycopg.Connection[tuple[object, ...]],
    *,
    email: str,
    display_name: str,
    role: OperatorRole,
    password_hash: str,
) -> str:
    row = connection.execute(
        "SELECT id FROM operators WHERE lower(email) = lower(%s)", (email,)
    ).fetchone()
    if row is None:
        operator_id = f"operator-{uuid4()}"
        connection.execute(
            """INSERT INTO operators (id, email, display_name, role, password_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (operator_id, email, display_name, role, password_hash),
        )
        return operator_id
    operator_id = str(row[0])
    connection.execute(
        """UPDATE operators
           SET email = %s, display_name = %s, role = %s, password_hash = %s,
               is_active = true, updated_at = now()
           WHERE id = %s""",
        (email, display_name, role, password_hash, operator_id),
    )
    connection.execute(
        "UPDATE user_sessions SET revoked_at = now() WHERE operator_id = %s AND revoked_at IS NULL",
        (operator_id,),
    )
    return operator_id


def _replace_memberships(
    connection: psycopg.Connection[tuple[object, ...]],
    operator_id: str,
    workspace_ids: list[str],
) -> None:
    existing = {
        str(row[0])
        for row in connection.execute(
            "SELECT id FROM store_workspaces WHERE id = ANY(%s)", (workspace_ids,)
        ).fetchall()
    }
    missing = set(workspace_ids) - existing
    if missing:
        raise SystemExit(f"工作区不存在：{', '.join(sorted(missing))}")
    connection.execute("DELETE FROM workspace_memberships WHERE operator_id = %s", (operator_id,))
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO workspace_memberships (operator_id, workspace_id) VALUES (%s, %s)",
            [(operator_id, workspace_id) for workspace_id in workspace_ids],
        )


if __name__ == "__main__":
    main()
