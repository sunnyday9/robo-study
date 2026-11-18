import { HtmlBasePlugin } from "@11ty/eleventy";

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(HtmlBasePlugin);
  eleventyConfig.addPassthroughCopy({ "site/assets": "assets" });
}

export const config = {
  dir: { input: "site", output: "dist" },
};
