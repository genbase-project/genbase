import React, { useState, useEffect } from 'react';
import { Tree, NodeRendererProps } from 'react-arborist';
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, Folder, File, Plus, FolderPlus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Module, MoveParams, TreeNode, TreeView } from '../TreeView';



interface SidebarProps {
  initialTree?: TreeNode[];
  initialModules?: Module[];
}


// Default modules for testing if none provided
const DEFAULT_MODULES: Module[] = [
  {
    name: "Module 1",
    version: "1.0.0",
    created_at: "2023-01-01",
    size: 1024,
    owner: "John Doe"
  },
  {
    name: "Module 2",
    version: "2.0.0",
    created_at: "2023-01-02",
    size: 2048,
    owner: "Jane Doe"
  },
  {
    name: "Module 3",
    version: "1.1.0",
    created_at: "2023-01-03",
    size: 3072,
    owner: "Jim Smith"
  }
];

// Default tree structure for testing if none provided
const DEFAULT_TREE: TreeNode[] = [
  {
    id: "folder-1",
    name: "Folder 1",
    isFolder: true,
    children: [
      {
        id: "item-1",
        name: "Module 1",
        module: DEFAULT_MODULES[0]
      }
    ]
  },
  {
    id: "folder-2",
    name: "Folder 2",
    isFolder: true,
    children: []
  }
];

const Sidebar: React.FC<SidebarProps> = ({ 
  initialTree = DEFAULT_TREE,
  initialModules = DEFAULT_MODULES 
}) => {
  const [data, setData] = useState<TreeNode[]>(initialTree);
  const [modules, setModules] = useState<Module[]>(initialModules);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [currentParentId, setCurrentParentId] = useState<string | null>(null);
  


  const fetchModules = async () => {
    try {
      const response = await fetch('http://localhost:8000/module');
      const result = await response.json();
      setModules(result.modules);
    } catch (error) {
      console.error('Error fetching modules:', error);
      // Keep using initial modules if fetch fails
      setModules(initialModules);
    }
  };

  const handleModuleClick = (module: Module) => {
    console.log('Selected module:', module);
  };

  const createFolder = (parentId: string | null) => {
    const newFolder: TreeNode = {
      id: `folder-${Date.now()}`,
      name: 'New Folder',
      children: [],
      isFolder: true
    };

    if (parentId === null) {
      setData([...data, newFolder]);
    } else {
      setData(prev => {
        const updateNodes = (nodes: TreeNode[]): TreeNode[] => {
          return nodes.map(node => {
            if (node.id === parentId) {
              return {
                ...node,
                children: [...(node.children || []), newFolder]
              };
            }
            if (node.children) {
              return {
                ...node,
                children: updateNodes(node.children)
              };
            }
            return node;
          });
        };
        return updateNodes(prev);
      });
    }
  };

  const handleCreateModule = (parentId: string | null) => {


    fetchModules();
    setCurrentParentId(parentId);
    setIsDialogOpen(true);
  };

  const createItem = (parentId: string | null, selectedModule: string) => {
    const module = modules.find(m => m.name === selectedModule);
    if (!module) return;

    const newNode: TreeNode = {
      id: `item-${Date.now()}`,
      name: module.name,
      module: module,
      isFolder: false
    };

    if (parentId === null) {
      setData([...data, newNode]);
    } else {
      setData(prev => {
        const updateNodes = (nodes: TreeNode[]): TreeNode[] => {
          return nodes.map(node => {
            if (node.id === parentId) {
              return {
                ...node,
                children: [...(node.children || []), newNode]
              };
            }
            if (node.children) {
              return {
                ...node,
                children: updateNodes(node.children)
              };
            }
            return node;
          });
        };
        return updateNodes(prev);
      });
    }
  };

  const handleMove = ({ dragIds, parentId, index }: MoveParams) => {
    setData(prev => {
      const findNodeById = (nodes: TreeNode[], id: string): TreeNode | null => {
        for (const node of nodes) {
          if (node.id === id) return node;
          if (node.children) {
            const found = findNodeById(node.children, id);
            if (found) return found;
          }
        }
        return null;
      };

      const removeNodeById = (nodes: TreeNode[], id: string): [TreeNode[], TreeNode | null] => {
        let removedNode: TreeNode | null = null;
        
        const filterNodes = (nodes: TreeNode[]): TreeNode[] => {
          return nodes.reduce((acc: TreeNode[], node) => {
            if (node.id === id) {
              removedNode = node;
              return acc;
            }
            
            if (node.children) {
              const filteredChildren = filterNodes(node.children);
              if (filteredChildren.length !== node.children.length || removedNode) {
                acc.push({ ...node, children: filteredChildren });
              } else {
                acc.push(node);
              }
            } else {
              acc.push(node);
            }
            return acc;
          }, []);
        };

        const updatedNodes = filterNodes(nodes);
        return [updatedNodes, removedNode];
      };

      const insertNodesAt = (nodes: TreeNode[], targetParentId: string | null, targetIndex: number, nodesToInsert: TreeNode[]): TreeNode[] => {
        if (targetParentId === null) {
          const result = [...nodes];
          result.splice(targetIndex, 0, ...nodesToInsert);
          return result;
        }

        return nodes.map(node => {
          if (node.id === targetParentId) {
            const children = [...(node.children || [])];
            children.splice(targetIndex, 0, ...nodesToInsert);
            return { ...node, children };
          }
          if (node.children) {
            return {
              ...node,
              children: insertNodesAt(node.children, targetParentId, targetIndex, nodesToInsert)
            };
          }
          return node;
        });
      };

      const isDescendant = (nodeId: string, potentialAncestorId: string): boolean => {
        const node = findNodeById(prev, potentialAncestorId);
        if (!node || !node.children) return false;

        return node.children.some(child => 
          child.id === nodeId || (child.children && isDescendant(nodeId, child.id))
        );
      };

      if (parentId && dragIds.some(dragId => isDescendant(parentId, dragId))) {
        return prev;
      }

      let intermediate = [...prev];
      const nodesToMove: TreeNode[] = [];

      for (const dragId of dragIds) {
        const [updatedNodes, removedNode] = removeNodeById(intermediate, dragId);
        if (removedNode) {
          nodesToMove.push(removedNode);
          intermediate = updatedNodes;
        }
      }

      return insertNodesAt(intermediate, parentId, index, nodesToMove);
    });
  };

  const handleCreateConfirm = () => {
    if (selectedModule) {
      createItem(currentParentId, selectedModule);
    }
    setIsDialogOpen(false);
    setSelectedModule(null);
  };

  return (
    <>
     

      <TreeView
        data={data}
        modules={modules}
        allowDrag={true}
        onCreateFolder={createFolder}
        onCreateModule={handleCreateModule}
        onModuleClick={handleModuleClick}
        onMove={handleMove}
      />

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Select Module</DialogTitle>
          </DialogHeader>
          <Select value={selectedModule || ''} onValueChange={setSelectedModule}>
            <SelectTrigger>
              <SelectValue placeholder="Select a module" />
            </SelectTrigger>
            <SelectContent>
              {modules.map((module) => (
                <SelectItem key={module.name} value={module.name}>
                  {module.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateConfirm} disabled={!selectedModule}>
              Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default Sidebar;