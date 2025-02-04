import React, { useState, useMemo } from 'react';
import { Tree, NodeRendererProps } from 'react-arborist';
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, Plus, Pencil, Box, Search } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '@/lib/utils';
import { Input } from './ui/input';

export interface EnvVar {
  name: string;
  optional?: boolean;
  default?: any;
}

export interface Kit {
  name: string;
  version: string;
  created_at: string;
  size: number;
  owner: string;
  doc_version: string;
  kit_id: string;
  environment: EnvVar[];
}

export interface Module {
  module_id: string;
  project_id: string;
  kit_id: string;
  owner: string;
  version: string;
  created_at: string;
  env_vars: Record<string, string>;
  repo_name: string;
  path: string;
  module_name: string;
}

export interface TreeNode {
  id: string;
  name: string;
  children?: TreeNode[];
  isFolder?: boolean;
  kit?: Kit;
  module?: Module;
}

export interface MoveParams {
  dragIds: string[];
  parentId: string | null;
  index: number;
}

export interface TreeViewProps {
  data: TreeNode[];
  modules: Kit[];
  allowDrag?: boolean;
  onCreateModule?: ((parentId: string | null) => void) | null;
  onModuleClick: (module: Module) => void;
  onMove?: (params: MoveParams) => void;
  onEditPath?: (module: Module) => void;
  onRename?: (moduleId: string, currentName: string) => void;
  isLoading?: boolean;
  selectedModuleId?: string | null;
}


// Helper function to recursively filter tree nodes
const filterNodes = (nodes: TreeNode[], searchText: string): TreeNode[] => {
  return nodes.reduce<TreeNode[]>((acc, node) => {
    const matchesSearch = node.name.toLowerCase().includes(searchText.toLowerCase());
    
    if (node.children) {
      const filteredChildren = filterNodes(node.children, searchText);
      if (matchesSearch || filteredChildren.length > 0) {
        acc.push({
          ...node,
          children: filteredChildren
        });
      }
    } else if (matchesSearch) {
      acc.push(node);
    }
    
    return acc;
  }, []);
};

export const TreeView: React.FC<TreeViewProps> = ({
  data,
  modules,
  allowDrag = true,
  onCreateModule,
  onModuleClick,
  onMove,
  onEditPath,
  onRename,
  isLoading = false,
  selectedModuleId = null
}) => {
  const [searchText, setSearchText] = useState('');

  const filteredData = useMemo(() => {
    if (!searchText.trim()) return data;
    return filterNodes(data, searchText);
  }, [data, searchText]);

  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeNode>>((props, ref) => {
    const { node, style, dragHandle } = props;
    const [showActions, setShowActions] = useState(false);
    
    const isSelected = !node.data.isFolder && 
      node.data.module?.module_id === selectedModuleId;
    
    return (
      <div 
        style={style} 
        ref={(element) => {
          if (allowDrag && dragHandle) dragHandle(element);
          if (typeof ref === 'function') ref(element);
          else if (ref) ref.current = element;
        }}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
        data-id={node.id}
      >
        <div 
          className={cn(
            "flex items-center justify-between py-1.5 px-2 h-8",
            "rounded-sm mx-0 transition-colors",
            "hover:bg-gray-200/50 group rounded-md",
            isSelected && "bg-gray-200/60"
          )}
        >
          <div 
            className="flex items-center gap-1.5 flex-1 min-w-0 cursor-pointer"
            onClick={() => {
              if (node.data.isFolder) {
                node.toggle();
              } else if (node.data.module) {
                onModuleClick(node.data.module);
              }
            }}
          >
            {node.data.isFolder ? (
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-5 w-5 p-0 hover:bg-transparent"
                onClick={(e) => {
                  e.stopPropagation();
                  node.toggle();
                }}
              >
                {node.isOpen ? 
                  <ChevronDown className="h-3.5 w-3.5 text-gray-500" /> : 
                  <ChevronRight className="h-3.5 w-3.5 text-gray-500" />
                }
              </Button>
            ) : (
              <Box className="h-3.5 w-3.5 ml-1 text-gray-400 shrink-0" />
            )}
            <span className="text-sm text-gray-700 truncate">{node.data.name}</span>
          </div>

          {showActions && (onCreateModule || onEditPath || onRename) && (
            <div className="flex gap-1">
              {node.data.isFolder && onCreateModule && (
                <Button 
                  variant="ghost" 
                  size="icon"
                  className="h-6 w-6 rounded-full hover:bg-gray-200/70 hover:text-gray-800 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCreateModule(node.id);
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              )}
              {!node.data.isFolder && node.data.module && (
                <>
                  {onRename && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 rounded-full hover:bg-gray-200/70 hover:text-gray-800 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRename(node.id, node.data.name);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  {onEditPath && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 rounded-full hover:bg-gray-200/70 hover:text-gray-800 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditPath(node.data.module!);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    );
  });

  Node.displayName = 'Node';

  if (isLoading) {
    return (
      <div className="h-full bg-gray-50/60 border-none">
        <div className="p-3 text-sm text-gray-500 text-center">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50/60">
      <div className="p-2 flex items-center  ">
        <div className="flex items-center gap-2 px-2 py-1.5 bg-white/50 border border-gray-200/80 rounded-xl w-full">
          <Search className="w-4 h-4 text-gray-500" />
          <Input
            type="text"
            placeholder="Search modules..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="h-6 text-sm bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 border-none shadow-none w-full placeholder:text-gray-400"
          />
        </div>
      </div>
      {onCreateModule && (
        <div className="pt-2 px-2 pb-1 flex items-center justify-between  border-gray-200/80">
          <span><p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Modules</p></span>
          <Button 
            variant="ghost" 
            size="icon"
            className="h-6 w-6 rounded-full hover:bg-gray-200/70 hover:text-gray-800 transition-colors"
            onClick={() => onCreateModule(null)}
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      <ScrollArea className="flex-1">
        {data.length === 0 ? (
          <div className="p-3 text-sm text-gray-500 text-center">
            No modules yet. Click the plus button to add one.
          </div>
        ) : (
          <Tree<TreeNode>
            data={filteredData}
            onMove={allowDrag ? onMove : undefined}
            width="100%"
            height={800}
            indent={16}
            rowHeight={32}
            overscanCount={5}
          >
            {Node}
          </Tree>
        )}
      </ScrollArea>
    </div>
  );
};
