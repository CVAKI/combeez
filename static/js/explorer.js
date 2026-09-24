// Renders the real file tree for the current module and loads real file
// contents into the code viewer with syntax highlighting via highlight.js.

const ICONS = { dir: "folder", file: "description" };

function fileIcon(name) {
  if (name.endsWith(".py")) return "data_object";
  if (name.endsWith(".ts") || name.endsWith(".tsx") || name.endsWith(".js")) return "code";
  if (name.endsWith(".json") || name.endsWith(".yaml") || name.endsWith(".yml")) return "tune";
  if (name.endsWith(".md")) return "description";
  return "insert_drive_file";
}

function renderNode(node, depth) {
  const wrap = document.createElement("div");
  wrap.style.marginLeft = depth === 0 ? "0" : "12px";

  if (node.type === "dir") {
    const row = document.createElement("div");
    row.className = "flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low cursor-pointer text-on-surface-variant";
    row.innerHTML = `<span class="material-symbols-outlined text-sm text-outline">folder_open</span><span class="${depth === 0 ? 'font-semibold text-on-surface' : ''}">${node.name}</span>`;
    const childrenBox = document.createElement("div");
    row.addEventListener("click", () => childrenBox.classList.toggle("hidden"));
    wrap.appendChild(row);
    wrap.appendChild(childrenBox);
    node.children.forEach(child => childrenBox.appendChild(renderNode(child, depth + 1)));
  } else {
    const row = document.createElement("div");
    row.className = "flex items-center justify-between px-2 py-1 rounded hover:bg-surface-container-low cursor-pointer text-on-surface-variant hover:text-on-surface";
    row.innerHTML = `<span class="flex items-center gap-1.5"><span class="material-symbols-outlined text-sm text-outline">${fileIcon(node.name)}</span>${node.name}</span>`;
    row.addEventListener("click", () => loadFile(node.path, row));
    wrap.appendChild(row);
  }
  return wrap;
}

let activeRow = null;

async function loadFile(path, rowEl) {
  if (activeRow) activeRow.classList.remove("bg-surface-container", "text-primary");
  rowEl.classList.add("bg-surface-container", "text-primary");
  activeRow = rowEl;

  const res = await fetch(`/api/module/${MODULE_KEY}/file?path=${encodeURIComponent(path)}`);
  const codeEl = document.getElementById("codeView");
  if (!res.ok) {
    codeEl.textContent = `# Could not load ${path}`;
    return;
  }
  const data = await res.json();
  document.getElementById("currentPath").textContent = data.path;
  document.getElementById("fileMeta").textContent = `${data.lines} lines · ${data.size} bytes · ${data.language}`;
  codeEl.className = `hljs language-${data.language}`;
  codeEl.textContent = data.content;
  if (window.hljs) hljs.highlightElement(codeEl);
}

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("fileTree");
  if (TREE.children && TREE.children.length) {
    TREE.children.forEach(child => container.appendChild(renderNode(child, 0)));
  } else {
    container.innerHTML = `<div class="text-outline px-2 py-1">Empty — drop ${MODULE_KEY} source files into this folder.</div>`;
  }
});
