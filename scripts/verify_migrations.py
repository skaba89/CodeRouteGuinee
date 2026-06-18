import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def run(command: list[str], env: dict[str, str]) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=BACKEND, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CodeRoute Alembic migrations from an empty database.")
    parser.add_argument("--keep-db", action="store_true", help="Keep the generated SQLite database for inspection.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        database_path = Path(tmpdir) / "coderoute-migration-check.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
        env["AUTO_CREATE_TABLES"] = "false"
        env["ENVIRONMENT"] = "development"
        env["ALLOW_DEMO_SEED_NON_DEV"] = "true"

        python = sys.executable
        run([python, "-m", "alembic", "upgrade", "head"], env)
        run([python, "-m", "pytest", "tests/test_database_migrations.py", "-q"], env)
        run([python, "-m", "app.seed_demo"], env)

        if args.keep_db:
            target = ROOT / "migration-check.db"
            target.write_bytes(database_path.read_bytes())
            print(f"Database kept at {target}")

    print("Migration verification completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
