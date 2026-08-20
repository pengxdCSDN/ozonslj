"""说明本模块的职责、边界和主要协作对象。"""

from uuid import uuid4

from psycopg import Connection


class BootstrapRoleRequiredError(RuntimeError):
    """数据库连接不是专用引导角色，禁止绕过强制 RLS 创建首个所有者。"""


def provision_organization_owner(
    connection: Connection[tuple[object, ...]],
    *,
    organization_id: str,
    organization_name: str,
    email: str,
    display_name: str,
    password_hash: str,
) -> str:
    """使用专用高权限连接原子创建或更新组织所有者，并撤销其旧会话。

Args:
    connection: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    organization_name: 参数语义、输入边界和安全约束。
    email: 参数语义、输入边界和安全约束。
    display_name: 参数语义、输入边界和安全约束。
    password_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    _require_bootstrap_role(connection)
    normalized_email = email.strip().lower()
    with connection.transaction():
        connection.execute(
            """
            INSERT INTO organizations (id, name, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name, status = 'active', updated_at = CURRENT_TIMESTAMP
            """,
            (organization_id, organization_name.strip()),
        )
        row = connection.execute(
            "SELECT id FROM users WHERE email = %s",
            (normalized_email,),
        ).fetchone()
        user_id = str(row[0]) if row is not None else f"user-{uuid4()}"
        connection.execute(
            """
            INSERT INTO users (
                id, email, display_name, password_hash, status, email_verified_at
            ) VALUES (%s, %s, %s, %s, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                password_hash = EXCLUDED.password_hash,
                status = 'active',
                email_verified_at = COALESCE(users.email_verified_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, normalized_email, display_name.strip(), password_hash),
        )
        connection.execute(
            """
            INSERT INTO organization_members (organization_id, user_id, role, status)
            VALUES (%s, %s, 'owner', 'active')
            ON CONFLICT (organization_id, user_id) DO UPDATE
            SET role = 'owner', status = 'active', updated_at = CURRENT_TIMESTAMP
            """,
            (organization_id, user_id),
        )
        connection.execute(
            """
            UPDATE user_sessions
            SET revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP)
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (user_id,),
        )
    return user_id


def _require_bootstrap_role(connection: Connection[tuple[object, ...]]) -> None:
    """执行内部步骤 _require_bootstrap_role，供同一模块的公开流程复用。

Args:
    connection: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    BootstrapRoleRequiredError: 业务约束或外部依赖失败时抛出。
"""
    row = connection.execute(
        """
        SELECT rolsuper, rolbypassrls
        FROM pg_roles
        WHERE rolname = CURRENT_USER
        """
    ).fetchone()
    if row is None or not (bool(row[0]) or bool(row[1])):
        raise BootstrapRoleRequiredError(
            "首个组织所有者只能使用独立的 BYPASSRLS/超级用户引导连接创建"
        )
