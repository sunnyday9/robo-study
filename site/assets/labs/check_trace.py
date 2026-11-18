import argparse
import csv
from pathlib import Path


FIELDS = {"episode", "frame", "obs_ns", "command_ns", "gripper"}


def validate(path: Path, max_skew_ns: int) -> tuple[int, int]:
    episodes: set[str] = set()
    current_episode = None
    count = 0
    with path.open(newline="", encoding="utf-8") as source:
        rows = csv.DictReader(source)
        if not rows.fieldnames or set(rows.fieldnames) != FIELDS or len(rows.fieldnames) != len(FIELDS):
            raise ValueError("unexpected CSV fields")
        for row in rows:
            line = rows.line_num
            if not all(row.get(field) for field in FIELDS) or None in row:
                raise ValueError(f"line {line}: incomplete or extra cells")
            episode = row["episode"]
            if episode != current_episode:
                if episode in episodes:
                    raise ValueError(f"line {line}: episode is split across the file")
                episodes.add(episode)
                current_episode = episode
                expected_frame, previous_obs, previous_command = 0, -1, -1
            try:
                frame, obs, command = (int(row[field]) for field in ("frame", "obs_ns", "command_ns"))
            except ValueError as error:
                raise ValueError(f"line {line}: frame and stamps must be integers") from error
            if frame != expected_frame:
                raise ValueError(f"line {line}: expected frame {expected_frame}, got {frame}")
            if obs <= previous_obs or command <= previous_command:
                raise ValueError(f"line {line}: episode stamps must strictly increase")
            if not 0 <= command - obs <= max_skew_ns:
                raise ValueError(f"line {line}: observation-to-command skew outside budget")
            if row["gripper"] not in {"open", "close", "hold"}:
                raise ValueError(f"line {line}: unknown gripper command")
            expected_frame, previous_obs, previous_command = frame + 1, obs, command
            count += 1
    if not count:
        raise ValueError("no trace rows")
    return count, len(episodes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the capstone's toy trace contract")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--max-skew-ns", type=int, default=10_000_000)
    args = parser.parse_args()
    if args.max_skew_ns < 0:
        parser.error("--max-skew-ns must be nonnegative")
    try:
        rows, episodes = validate(args.trace, args.max_skew_ns)
    except (OSError, ValueError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"OK: {rows} rows across {episodes} episodes")


if __name__ == "__main__":
    main()
