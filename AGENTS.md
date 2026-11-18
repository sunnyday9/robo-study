## Agent skills

### Issue tracker

Track work in GitHub Issues. Before creating, reading, or updating issues, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels. Before triaging, read `docs/agents/triage-labels.md`.

### Domain docs

Use a single context: root `CONTEXT.md` and `docs/adr/`. Before exploring or changing domain behavior, read `docs/agents/domain.md`.

## Publishing

After verifying each requested site adjustment, publish it to the existing Vercel project. Push the intended changes to `main`, then verify that the matching Git-triggered production deployment serves the update at https://robo-study.vercel.app/. Respect explicit requests for local-only work.
