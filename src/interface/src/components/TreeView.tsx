import React, { useState } from 'react';
import { Tree, NodeRendererProps } from 'react-arborist';
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, Plus, Pencil, Box } from 'lucide-react';

export interface EnvVar {
  name: string;
  optional?: boolean;
  default?: any;
}

export interface Module {
  name: string;
  version: string;
  created_at: string;
  size: number;
  owner: string;
  doc_version: string;
  module_id: string;
  environment: EnvVar[];
}

export interface RuntimeModule {
  id: string;
  project_id: string;
  module_id: string;
  owner: string;
  version: string;
  created_at: string;
  env_vars: Record<string, string>;
  repo_name: string;
  path: string;
}

export interface TreeNode {
  id: string;
  name: string;
  children?: TreeNode[];
  isFolder?: boolean;
  module?: Module;
  runtimeModule?: RuntimeModule;
}

export interface MoveParams {
  dragIds: string[];
  parentId: string | null;
  index: number;
}

export interface TreeViewProps {
  data: TreeNode[];
  modules: Module[];
  allowDrag?: boolean;
  onCreateModule?: ((parentId: string | null) => void) | null;
  onModuleClick: (runtimeModule: RuntimeModule) => void;
  onMove?: (params: MoveParams) => void;
  onEditPath?: (runtimeModule: RuntimeModule) => void;
  isLoading?: boolean;
  selectedModuleId?: string | null;
}

export const TreeView: React.FC<TreeViewProps> = ({
  data,
  modules,
  allowDrag = true,
  onCreateModule,
  onModuleClick,
  onMove,
  onEditPath,
  isLoading = false,
  selectedModuleId = null
}) => {
  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeNode>>((props, ref) => {
    const { node, style, dragHandle } = props;
    const [showActions, setShowActions] = useState(false);
    
    const isSelected = !node.data.isFolder && 
      node.data.runtimeModule?.id === selectedModuleId;
    
    return (
      <div 
        style={style} 
        ref={(element) => {
          if (allowDrag && dragHandle) dragHandle(element);
          if (typeof ref === 'function') ref(element);
          else if (ref) ref.current = element;
        }}
        className={`flex items-center justify-between py-0.5 px-1 hover:bg-gray-100 group
          ${isSelected ? 'bg-blue-50 hover:bg-blue-100' : ''}`}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
        data-id={node.id}
      >
        <div 
          className="flex items-center gap-1 cursor-pointer flex-1"
          onClick={() => {
            if (node.isInternal) {
              node.toggle();
            } else if (node.data.runtimeModule) {
              onModuleClick(node.data.runtimeModule);
            }
          }}
        >
          {node.data.isFolder ? (
            <>
              {node.isOpen ? 
                <ChevronDown className="h-3 w-3 text-gray-400" /> : 
                <ChevronRight className="h-3 w-3 text-gray-400" />
              }
            </>
          ) : (
            <Box className="h-3 w-3 text-gray-400 ml-3" />
          )}
          <span className="text-sm overflow-hidden whitespace-nowrap overflow-ellipsis">{node.data.name}</span>
        </div>

        {showActions && onCreateModule && (
          <div className="flex gap-0.5">
            {node.data.isFolder && (
              <Button 
                variant="ghost" 
                size="icon"
                className="h-5 w-5"
                onClick={(e) => {
                  e.stopPropagation();
                  onCreateModule(node.id);
                }}
              >
                <Plus className="h-3 w-3" />
              </Button>
            )}
            {!node.data.isFolder && node.data.runtimeModule && onEditPath && (
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditPath(node.data.runtimeModule!);
                }}
              >
                <Pencil className="h-3 w-3" />
              </Button>
            )}
          </div>
        )}
      </div>
    );
  });

  Node.displayName = 'Node';

  if (isLoading) {
    return (
      <div className="h-screen min-w-48 bg-white border-r flex flex-col">
        <div className="p-2 text-center text-gray-500 text-sm">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen min-w-48 bg-white border-r flex flex-col">
      {onCreateModule && (
        <div className="p-1.5 border-b flex justify-between items-center flex-shrink-0 text-gray-700">
          <span className="font-semibold text-sm">PROJECT</span>
          <div className="flex gap-0.5">
            <Button 
              variant="ghost" 
              size="icon"
              className="h-5 w-5"
              onClick={() => onCreateModule(null)}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

<div className="flex-1 overflow-auto hover:overflow-overlay" style={{
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgb(209 213 219 / 0.4) transparent'
        }}>
        {data.length === 0 ? (
          <div className="p-2 text-center text-gray-500 text-sm">
            No items yet. Click the plus button to add a module.
          </div>
        ) : (
          <Tree<TreeNode>
            data={data}
            onMove={allowDrag ? onMove : undefined}
            width="100%"
            height={800}
            indent={16}
            rowHeight={24}
            overscanCount={1}
          >
            {Node}
          </Tree>
        )}
      </div>
    </div>
  );
};