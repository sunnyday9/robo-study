import { HtmlBasePlugin, IdAttributePlugin } from "@11ty/eleventy";

function localizedUrl(url, locale) {
  const neutral = url.replace(/^\/zh(?=\/)/, "");
  return locale === "zh-CN" ? `/zh${neutral}` : neutral;
}

export default function (eleventyConfig) {
  eleventyConfig.addFilter("localizedUrl", localizedUrl);
  eleventyConfig.addFilter("localizedNotes", (notes, locale) => notes
    .filter(note => (note.data.lang ?? "en") === locale)
    .sort((left, right) => left.data.order.localeCompare(right.data.order)));
  eleventyConfig.addPlugin(HtmlBasePlugin);
  eleventyConfig.addPlugin(IdAttributePlugin, {
    selector: "h2,h3",
    filter: ({ page }) => page.inputPath.startsWith("./site/notes/"),
  });
  eleventyConfig.addPlugin(IdAttributePlugin, {
    selector: "h2,h3",
    filter: ({ page }) => page.inputPath.startsWith("./site/zh/notes/"),
    slugify: value => value.normalize("NFKC").toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "") || "section",
  });
  eleventyConfig.addPassthroughCopy("site/assets/**/*.{css,js,svg,py,csv,cpp}");
}

export const config = {
  dir: { input: "site", output: "dist" },
};
