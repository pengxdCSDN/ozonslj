"""离线创建或更新首个组织所有者；不提供公网注册入口。"""

import argparse
import getpass
import os
from uuid import uuid4

import psycopg

from backend.app.application.identity import PasswordHasher
from backend.app.infrastructure.postgresql.bootstrap import provision_organization_owner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="创建或更新 ozonslj 组织所有者")
    parser.add_argument("--organization-id", default=f"org-{uuid4()}")
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    bootstrap_database_url = os.environ.get("BOOTSTRAP_DATABASE_URL")
    if not bootstrap_database_url:
        raise SystemExit("BOOTSTRAP_DATABASE_URL 未配置，拒绝使用普通应用连接引导所有者")
    password = getpass.getpass("密码（至少 12 个字符）: ")
    confirmation = getpass.getpass("再次输入密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")
    password_hash = PasswordHasher().hash(password)
    with psycopg.connect(bootstrap_database_url) as connection:
        user_id = provision_organization_owner(
            connection,
            organization_id=args.organization_id,
            organization_name=args.organization_name,
            email=args.email,
            display_name=args.display_name,
            password_hash=password_hash,
        )
    print(f"组织所有者已保存：organization_id={args.organization_id}，user_id={user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
