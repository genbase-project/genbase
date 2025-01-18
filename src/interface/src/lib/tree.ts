import { TreeNode, RuntimeModule } from '../components/TreeView';

export interface FolderNode {
  id: string;
  name: string;
  isFolder: true;
  children: (FolderNode | ModuleNode)[];
}

export interface ModuleNode {
  id: string;
  name: string;
  isFolder: false;
  runtimeModule: RuntimeModule;
}

export const DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000000";

export function buildTreeFromModules(modules: RuntimeModule[]): TreeNode[] {
  const folderMap = new Map<string, TreeNode>();
  const rootNodes: TreeNode[] = [];

  // Sort modules so that shorter paths are processed first
  const sortedModules = [...modules].sort((a, b) => a.path.length - b.path.length);

  sortedModules.forEach(module => {
    const pathParts = module.path.split('.');
    let currentPath = '';

    // Create or get all necessary folder nodes
    for (let i = 0; i < pathParts.length; i++) {
      const part = pathParts[i];
      currentPath = currentPath ? `${currentPath}.${part}` : part;
      
      if (!folderMap.has(currentPath)) {
        const newNode: TreeNode = {
          id: `folder-${currentPath}`,
          name: part,
          isFolder: true,
          children: []
        };
        folderMap.set(currentPath, newNode);

        // Add to parent or root
        if (i === 0) {
          rootNodes.push(newNode);
        } else {
          const parentPath = pathParts.slice(0, i).join('.');
          const parentNode = folderMap.get(parentPath);
          if (parentNode && parentNode.children) {
            parentNode.children.push(newNode);
          }
        }
      }
    }

    // Create module node
    const moduleNode: TreeNode = {
      id: `runtime-${module.id}`,
      name: `${module.module_id} (${module.version})`,
      isFolder: false,
      runtimeModule: module
    };

    // Add module node to its parent folder or root
    if (pathParts.length === 1) {
      rootNodes.push(moduleNode);
    } else {
      const parentFolder = folderMap.get(module.path);
      if (parentFolder && parentFolder.children) {
        parentFolder.children.push(moduleNode);
      }
    }
  });

  return rootNodes;
}

export function getParentPath(nodes: TreeNode[], nodeId: string): string {
  const parts: string[] = [];
  
  const findNode = (currentNodes: TreeNode[]): boolean => {
    for (const node of currentNodes) {
      if (node.id === nodeId) {
        return true;
      }
      
      if (node.children) {
        parts.push(node.name);
        if (findNode(node.children)) {
          return true;
        }
        parts.pop();
      }
    }
    return false;
  };

  findNode(nodes);
  return parts.join('.');
}

export function getNewPath(
  tree: TreeNode[], 
  dragId: string, 
  targetParentId: string | null, 
  targetIndex: number
): string {
  if (targetParentId === null) {
    return 'root';
  }

  const parentNode = findNodeById(tree, targetParentId);
  if (!parentNode || !parentNode.isFolder) {
    return 'root';
  }

  const parentPath = getParentPath(tree, targetParentId);
  if (!parentPath) {
    return parentNode.name;
  }

  return `${parentPath}.${parentNode.name}`;
}

export function findNodeById(nodes: TreeNode[], id: string): TreeNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

export function buildPathString(node: TreeNode, tree: TreeNode[]): string {
  const parts: string[] = [];
  
  const findNodePath = (nodes: TreeNode[], targetId: string): boolean => {
    for (const n of nodes) {
      if (n.id === targetId) {
        parts.unshift(n.name);
        return true;
      }
      if (n.children && findNodePath(n.children, targetId)) {
        parts.unshift(n.name);
        return true;
      }
    }
    return false;
  };

  findNodePath(tree, node.id);
  return parts.join('.');
}