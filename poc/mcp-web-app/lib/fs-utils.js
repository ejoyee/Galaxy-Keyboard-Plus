const fs = require('fs');
const path = require('path');

function directoryTree(dir, depth = 0) {
  if (depth > 7) return [];
  if (!fs.existsSync(dir)) return [];

  const children = fs.readdirSync(dir).map((file) => {
    const fullPath = path.join(dir, file);
    const stats = fs.statSync(fullPath);
    if (stats.isDirectory()) {
      return {
        type: 'directory',
        name: file,
        children: directoryTree(fullPath, depth + 1),
      };
    } else {
      return {
        type: 'file',
        name: file,
      };
    }
  });

  return children;
}

function readFilesWithExtension(dir, ext) {
  const result = [];

  function walk(current) {
    const files = fs.readdirSync(current);
    for (const file of files) {
      const fullPath = path.join(current, file);
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        walk(fullPath);
      } else if (file.endsWith(ext)) {
        result.push({
          path: fullPath,
          content: fs.readFileSync(fullPath, 'utf-8'),
        });
      }
    }
  }

  walk(dir);
  return result;
}

function renderMarkdownTree(tree, prefix = '', isLast = true) {
  return tree
    .map((node, index) => {
      const isLastItem = index === tree.length - 1;
      const connector = isLastItem ? '└── ' : '├── ';
      const subPrefix = prefix + (isLastItem ? '    ' : '│   ');
      const line = `${prefix}${connector}${node.name}`;

      if (node.children && node.children.length > 0) {
        const childrenTree = renderMarkdownTree(node.children, subPrefix, true);
        return [line, childrenTree].join('\n');
      } else {
        return line;
      }
    })
    .join('\n');
}

function applyEditFile({ path: filePath, new_content }) {
  fs.writeFileSync(filePath, new_content, 'utf-8');
}

module.exports = {
  directoryTree,
  readFilesWithExtension,
  applyEditFile,
  renderMarkdownTree,
};
