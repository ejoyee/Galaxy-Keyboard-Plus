const fs = require("fs");
const path = require("path");

// 생략할 디렉터리 목록
const excludeDirs = new Set([
  "node_modules",
  ".git",
  // 추가로 생략할 폴더가 있으면 여기에 적습니다.
]);

function directoryTree(dir, depth = 0) {
  if (depth > 7) return [];
  if (!fs.existsSync(dir)) return [];

  return fs.readdirSync(dir).map((file) => {
    const fullPath = path.join(dir, file);
    const stats = fs.statSync(fullPath);
    if (stats.isDirectory()) {
      // 생략 디렉터리면 children 없이 skipped 플래그만 남김
      if (excludeDirs.has(file)) {
        return { type: "directory", name: file, skipped: true };
      }
      return {
        type: "directory",
        name: file,
        children: directoryTree(fullPath, depth + 1),
      };
    } else {
      return {
        type: "file",
        name: file,
      };
    }
  });
}

function readFiles(dir, ext = "") {
  const result = [];
  const excludeDirs = new Set(["node_modules", ".git"]);

  function walk(current) {
    const base = path.basename(current);
    const stat = fs.statSync(current);

    // 1) 제외 디렉터리일 땐 중단
    if (stat.isDirectory() && excludeDirs.has(base)) {
      return;
    }

    if (stat.isDirectory()) {
      // 2) 디렉터리면 재귀
      for (const child of fs.readdirSync(current)) {
        walk(path.join(current, child));
      }
    } else {
      // 3) ext 검사: 빈 문자열, "*" 또는 배열 내 하나라도 매치되면 모두 통과
      let matchAll = ext === "" || ext === "*";
      if (!matchAll) {
        if (Array.isArray(ext)) {
          matchAll = ext.some((e) => current.endsWith(e));
        } else {
          matchAll = current.endsWith(ext);
        }
      }

      if (matchAll) {
        result.push({
          path: current,
          content: fs.readFileSync(current, "utf-8"),
        });
      }
    }
  }

  walk(dir);
  return result;
}

function renderMarkdownTree(tree, prefix = "", isLast = true) {
  return tree
    .map((node, index) => {
      const isLastItem = index === tree.length - 1;
      const connector = isLastItem ? "└── " : "├── ";
      const subPrefix = prefix + (isLastItem ? "    " : "│   ");
      const line = `${prefix}${connector}${node.name}${
        node.type === "directory" ? "/" : ""
      }`;

      // skipped 디렉터리면 바로 '...'
      if (node.skipped) {
        return `${line} ...`;
      }

      if (node.children && node.children.length > 0) {
        const childrenTree = renderMarkdownTree(node.children, subPrefix, true);
        return [line, childrenTree].join("\n");
      } else {
        return line;
      }
    })
    .join("\n");
}

function applyEditFile({ path: filePath, new_content }) {
  fs.writeFileSync(filePath, new_content, "utf-8");
}

module.exports = {
  directoryTree,
  readFiles,
  applyEditFile,
  renderMarkdownTree,
};
