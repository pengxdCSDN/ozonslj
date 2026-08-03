from scripts.create_operator import build_parser


def test_create_operator_defaults_to_admin_and_collects_workspaces() -> None:
    args = build_parser().parse_args(
        [
            "--email",
            "admin@example.com",
            "--display-name",
            "Admin",
            "--workspace",
            "workspace-1",
            "--workspace",
            "workspace-2",
        ]
    )

    assert args.role == "admin"
    assert args.workspace == ["workspace-1", "workspace-2"]
