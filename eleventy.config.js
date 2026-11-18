import { HtmlBasePlugin, IdAttributePlugin } from "@11ty/eleventy";

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(HtmlBasePlugin);
  eleventyConfig.addPlugin(IdAttributePlugin, {
    selector: "h2,h3",
    filter: ({ page }) => page.inputPath.startsWith("./site/notes/"),
  });
  eleventyConfig.addPassthroughCopy({ "site/assets": "assets" });
}

export const config = {
  dir: { input: "site", output: "dist" },
};
