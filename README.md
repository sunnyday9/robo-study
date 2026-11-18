# Robo Study

A lecture-based self-study course for developers who already know Python, data structures, and basic machine learning. Learn the reasoning and development process behind ROS 2, Isaac Sim, LeRobot, and robotics infrastructure. The browser labs and CPU capstone exercises need no robotics runtime.

## Preview locally

With Node.js 24 and npm installed:

```sh
npm ci
npm start
```

Open the local URL printed in the terminal. Run `npm run build` to generate the static site in `dist/`.

## Study order

Review frames, control, and projection if needed. Start ROS 2 on a supported CPU environment, then choose an Isaac Sim system using the compatibility guide. Use the LeRobot track to validate data and evaluate a baseline, and the infrastructure track when moving between machines or preparing reproducible runs. The tabletop capstone has separate replay, simulation, and learning gates; it does not require a real robot.

See [the course review](docs/course-review.md) for version choices and the distinction between locally run checks and expected lab results.

## Add a note

Create a Markdown file under `site/notes/`. Set `title`, `topic`, a short `description`, and an unused quoted `order` (for example, `"05"`) in its front matter. Use `prerequisites` and `minutes` for chapter metadata. The index groups chapters using `site/_data/tracks.json`; use an existing topic or add it to a track.

Start with a problem and an observable outcome. Explain the mechanics with a diagram or concrete trace, then walk through a small build and change one input intentionally. Label expected, illustrative, and measured results distinctly. Close with a transfer exercise and a concise summary. Put solutions in `<details>` blocks. Level-two headings appear in the lecture outline; link to other notes using paths like `/notes/coordinate-frames/`.

## Publish to Vercel

For a production deployment from this checkout, sign in with `npx vercel login`, then run `npx vercel deploy --prod`. Use the production domain returned by Vercel for the public site. Only the built `dist/` directory is served.

For automatic deployments, connect the GitHub repository in the existing Vercel project's **Settings → Git**. Set `main` as the production branch. The checked-in `vercel.json` specifies the Eleventy build and its output directory.

## Optional: GitHub Pages

To use GitHub Pages instead, set the Pages source to **GitHub Actions** in the repository's **Settings → Pages**, then run the Pages workflow manually from the **Actions** tab on `main`.

Report corrections or propose topics in [GitHub Issues](https://github.com/sunnyday9/robo-study/issues).
