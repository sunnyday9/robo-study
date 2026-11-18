# Issue tracker: GitHub

Track specs and tasks in GitHub Issues for `sunnyday9/robo-study`. Run `gh` from this clone so it resolves the repository from the remote.

| Operation | Command |
| --- | --- |
| Publish a spec or ticket | `gh issue create --title "..." --body-file <path>` |
| Fetch a ticket | `gh issue view <number> --comments` |
| List open tickets and their labels | `gh issue list --state open --json number,title,body,labels,comments` |
| Comment | `gh issue comment <number> --body "..."` |
| Change a label | `gh issue edit <number> --add-label <label>` or `--remove-label <label>` |
| Close | `gh issue close <number> --comment "..."` |

## Pull requests as a triage surface

**PRs as a request surface: no.** Triage GitHub Issues, not pull requests.

## Wayfinding

- Use an issue labeled `wayfinder:map` for the map and GitHub sub-issues for tickets. If sub-issues are unavailable, use a task list in the map and link to its issue number from each ticket.
- Label tickets by type: `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task`.
- Record blockers with GitHub issue dependencies where available. The dependency API takes the blocker's database ID, not its issue number. Otherwise, record `Blocked by: #<number>` in the ticket body.
- Claim the first unassigned, unblocked ticket in map order with `gh issue edit <number> --add-assignee @me`. Record the result in the issue, close it, and link the outcome from the map.
