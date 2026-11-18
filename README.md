# Robo Study

A hands-on robotics textbook for developers who know basic Python but are new to robotics. Learn motion and control, perception and estimation, planning, ROS 2, simulation, robot learning, infrastructure, and field engineering. The first experiments and CPU capstone exercises need no robotics runtime.

## Preview locally

With Node.js 24 and npm installed:

```sh
npm ci
npm start
```

Open the local URL printed in the terminal. Run `npm run build` to generate the static site in `dist/`.

## Study order

Start with the first Python robot loop, then work through the common core in motion, sensing, estimation, and autonomy. Add ROS 2 and simulation when they answer an integration question. Use the career map to choose a specialty and the rover or tabletop capstone to build portfolio evidence. Physical operation calls for separate supervised practice.

See [the course review](docs/course-review.md) for version choices and the distinction between locally run checks and expected lab results.

## Add a note

Create a Markdown file under `site/notes/`. Set `title`, `topic`, a short `description`, and an unused quoted three-digit `order` in its front matter. Use `prerequisites` and `minutes` for chapter metadata. The index groups chapters using `site/_data/tracks.json`; use an existing topic or add it to a part.

Start with a problem and an observable outcome. Explain the mechanics with a diagram or concrete trace, then walk through a small build and change one input intentionally. Label expected, illustrative, and measured results distinctly. Close with a transfer exercise and a concise summary. Put solutions in `<details>` blocks. Level-two headings appear in the lecture outline; link to other notes using paths like `/notes/coordinate-frames/`.

## Publish to Vercel

For a production deployment from this checkout, sign in with `npx vercel login`, then run `npx vercel deploy --prod`. Use the production domain returned by Vercel for the public site. Only the built `dist/` directory is served.

For automatic deployments, connect the GitHub repository in the existing Vercel project's **Settings → Git**. Set `main` as the production branch. The checked-in `vercel.json` specifies the Eleventy build and its output directory.

## Optional: GitHub Pages

To use GitHub Pages instead, set the Pages source to **GitHub Actions** in the repository's **Settings → Pages**, then run the Pages workflow manually from the **Actions** tab on `main`.

Report corrections or propose topics in [GitHub Issues](https://github.com/sunnyday9/robo-study/issues).
