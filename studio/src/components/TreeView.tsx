import React, { useState, useMemo } from 'react';
import { Tree, NodeRendererProps } from 'react-arborist';
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, Plus, Pencil, Box, Search, Moon, Sun } from 'lucide-react';
import { ScrollArea, ScrollBar } from './ui/scroll-area';
import { cn } from '@/lib/utils';
import { Input } from './ui/input';
import { OpenMap } from 'react-arborist/dist/module/state/open-slice';

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
  defaultOpened?: boolean; // Add this new prop
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
  selectedModuleId = null,
  defaultOpened = true,
}) => {
  const [searchText, setSearchText] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(true);


  const initialOpenState = useMemo(() => {
    const openMap: OpenMap = {};
    // If defaultOpened is true, we could populate with open nodes
    // Otherwise leave empty for all closed
    return openMap;
  }, [defaultOpened]);


  const filteredData = useMemo(() => {
    if (!searchText.trim()) return data;
    return filterNodes(data, searchText);
  }, [data, searchText]);

  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeNode>>((props, ref) => {
    const { node, style, dragHandle } = props;
    const [showTools, setShowTools] = useState(false);
    
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
        onMouseEnter={() => setShowTools(true)}
        onMouseLeave={() => setShowTools(false)}
        data-id={node.id}
      >
        <div 
          className={cn(
            "flex items-center justify-between py-1.5 px-2 h-8",
            "rounded-sm mx-0 transition-colors",
          
            isSelected && (isDarkMode ? "bg-neutral-200" : "bg-neutral-200")
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
                className="h-5 w-5 p-0 "
                onClick={(e) => {
                  e.stopPropagation();
                  node.toggle();
                }}
              >
                {node.isOpen ? 
                  <ChevronDown className={`h-3.5 w-3.5 ${isDarkMode ? 'text-gray-800' : 'text-gray-900'}`} /> : 
                  <ChevronRight className={`h-3.5 w-3.5 ${isDarkMode ? 'text-gray-800' : 'text-gray-900'}`} />
                }
              </Button>
            ) : (
              <Box className={`h-3.5 w-3.5 ml-1 ${isDarkMode ? 'text-gray-900' : 'text-gray-800'} shrink-0`} />
            )}
            <span className={`text-sm ${ 'text-gray-700'} truncate`}>
              {node.data.name}
            </span>
          </div>

          {showTools && (onCreateModule || onEditPath || onRename) && (
            <div className="flex gap-1">
              {node.data.isFolder && onCreateModule && (
                <Button 
                  variant="ghost" 
                  size="icon"
                  className={cn(
                    "h-6 w-6 rounded-full transition-colors",
                   "hover:bg-neutral-200 hover:text-gray-800"
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
                     "hover:bg-neutral-200/70 hover:text-gray-800"
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
                       "hover:bg-neutral-200 hover:text-gray-200" 
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
    "bg-neutral-200 "
      )}>
        <div className={cn(
          "p-3 text-sm text-center",
         "text-gray-800"
        )}>
          Loading...
        </div>
      </div>
    );
  }

    return (
      <div className={cn(
        "h-full flex flex-col",
  "bg-neutral-50"
      )}>
        {/* Search Bar */}
        <div className="p-2">
          <div className={cn(
            "flex items-center gap-2 px-2 py-1.5 border rounded-xl w-full",
         "bg-neutral-200" 
          )}>
            <Search className={isDarkMode ? "w-4 h-4 text-gray-800" : "w-4 h-4 text-gray-900"} />
            <Input
              type="text"
              placeholder="Search modules..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className={cn(
                "h-6 text-sm  focus-visible:ring-0 focus-visible:ring-offset-0 border-none shadow-none w-full",
           "text-gray-700 placeholder:text-gray-900" 
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
                "h-8 w-full  transition-colors border-1 border-gray-300 ",
               "text-gray-700 hover:bg-neutral-200 hover:text-gray-800"
              )}
              onClick={() => onCreateModule(null)}
            >
              
              <p className={cn(
                "text-xs   tracking-wide",
                isDarkMode ? "text-gray-800" : "text-gray-600"
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
                isDarkMode ? "text-gray-800" : "text-gray-900"
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
               initialOpenState={initialOpenState}
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
  