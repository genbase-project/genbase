import React, { useState, useMemo } from 'react';
import { Tree, NodeRendererProps } from 'react-arborist';
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, Plus, Pencil, Box, Search, Moon, Sun } from 'lucide-react';
import { ScrollArea, ScrollBar } from './ui/scroll-area';
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
  const [isDarkMode, setIsDarkMode] = useState(true);

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
            isDarkMode 
              ? "hover:bg-neutral-800/50 group rounded-md"
              : "hover:bg-neutral-200/50 group rounded-md",
            isSelected && (isDarkMode ? "bg-neutral-800/60" : "bg-neutral-200/60")
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
                  <ChevronDown className={`h-3.5 w-3.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} /> : 
                  <ChevronRight className={`h-3.5 w-3.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                }
              </Button>
            ) : (
              <Box className={`h-3.5 w-3.5 ml-1 ${isDarkMode ? 'text-gray-500' : 'text-gray-400'} shrink-0`} />
            )}
            <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} truncate`}>
              {node.data.name}
            </span>
          </div>

          {showActions && (onCreateModule || onEditPath || onRename) && (
            <div className="flex gap-1">
              {node.data.isFolder && onCreateModule && (
                <Button 
                  variant="ghost" 
                  size="icon"
                  className={cn(
                    "h-6 w-6 rounded-full transition-colors",
                    isDarkMode 
                      ? "hover:bg-neutral-700/70 hover:text-gray-200" 
                      : "hover:bg-neutral-200/70 hover:text-gray-800"
                  )}
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
                      className={cn(
                        "h-6 w-6 rounded-full transition-colors",
                        isDarkMode 
                          ? "hover:bg-neutral-700/70 hover:text-gray-200" 
                          : "hover:bg-neutral-200/70 hover:text-gray-800"
                      )}
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
                      className={cn(
                        "h-6 w-6 rounded-full transition-colors",
                        isDarkMode 
                          ? "hover:bg-neutral-700/70 hover:text-gray-200" 
                          : "hover:bg-neutral-200/70 hover:text-gray-800"
                      )}
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
      <div className={cn(
        "h-full border-none",
        isDarkMode ? "bg-neutral-900/60" : "bg-neutral-50/60"
      )}>
        <div className={cn(
          "p-3 text-sm text-center",
          isDarkMode ? "text-gray-400" : "text-gray-500"
        )}>
          Loading...
        </div>
      </div>
    );
  }

    return (
      <div className={cn(
        "h-full flex flex-col",
        isDarkMode ? "bg-neutral-900/60" : "bg-neutral-50/60"
      )}>
        {/* Search Bar */}
        <div className="p-2">
          <div className={cn(
            "flex items-center gap-2 px-2 py-1.5 border rounded-xl w-full",
            isDarkMode 
              ? "bg-neutral-800/50 border-gray-700/80" 
              : "bg-white/50 border-gray-200/80"
          )}>
            <Search className={isDarkMode ? "w-4 h-4 text-gray-400" : "w-4 h-4 text-gray-500"} />
            <Input
              type="text"
              placeholder="Search modules..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className={cn(
                "h-6 text-sm bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 border-none shadow-none w-full",
                isDarkMode 
                  ? "text-gray-200 placeholder:text-gray-500" 
                  : "text-gray-700 placeholder:text-gray-400"
              )}
            />
          </div>
        </div>
  
        {/* Create Module Header */}
        {onCreateModule && (
          <div className={cn(
            "px-2 pb-1 flex items-center justify-between",
            isDarkMode ? "border-gray-700/80" : "border-gray-200/80"
          )}>
           
            <Button 
              variant="ghost" 
              size="icon"
              className={cn(
                "h-8 w-full  transition-colors ",
                isDarkMode 
                  ? "text-gray-300 bg-neutral-800 hover:bg-neutral-700 hover:text-gray-200" 
                  : "text-gray-700 hover:bg-neutral-200/70 hover:text-gray-800"
              )}
              onClick={() => onCreateModule(null)}
            >
              
              <p className={cn(
                "text-xs   tracking-wide",
                isDarkMode ? "text-gray-400" : "text-gray-600"
              )}>
                Create Module
              </p>
         
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
  
        {/* Tree Content */}
        <ScrollArea className="flex-1">
          <div className="px-2">
            {data.length === 0 ? (
              <div className={cn(
                "p-3 text-sm text-center",
                isDarkMode ? "text-gray-400" : "text-gray-500"
              )}>
                No modules yet. Click the plus button to add one.
              </div>
            ) : (
              <div className="pr-4">
                <Tree<TreeNode>
                  data={filteredData}
                  onMove={allowDrag ? onMove : undefined}
                  width="100%"
                  height={500}
                  indent={16}
                  rowHeight={32}
                  overscanCount={5}
                >
                  {Node}
                </Tree>
              </div>
            )}
          </div>
          <ScrollBar orientation="vertical" />
        </ScrollArea>
      </div>
    );
  };

  export default TreeView;
  