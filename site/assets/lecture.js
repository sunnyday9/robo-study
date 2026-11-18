const outline = document.querySelector(".lecture-outline");
const outlineList = outline.querySelector("ol");
const sections = document.querySelectorAll(".lecture-body h2[id]");

for (const section of sections) {
  const item = document.createElement("li");
  const link = document.createElement("a");
  link.href = `#${encodeURIComponent(section.id)}`;
  link.textContent = section.textContent;
  item.append(link);
  outlineList.append(item);
}

outline.hidden = sections.length === 0;
