import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from groups_db import GroupsDB


def main() -> None:
    db = GroupsDB()
    print(f"Initialized groups database at {Path(db.db_path).resolve()}")


if __name__ == "__main__":
    main()
