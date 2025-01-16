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


export interface Module {
    name: string;
    version: string;
    created_at: string;
    size: number;
    owner: string;
  }

  
export interface TreeNode {
    id: string;
    name: string;
    children?: TreeNode[];
    isFolder?: boolean;
    module?: Module;
  }
  

export interface TreeViewProps {
    data: TreeNode[];
    modules: Module[];
    allowDrag?: boolean;
    onCreateFolder: (parentId: string | null) => void;
    onCreateModule: (parentId: string | null) => void;
    onModuleClick: (module: Module) => void;
    onMove?: (params: MoveParams) => void;
  }

  
export interface MoveParams {
    dragIds: string[];
    parentId: string | null;
    index: number;
  }

  

export const TreeView: React.FC<TreeViewProps> = ({
  data,
  allowDrag = true,
  onCreateFolder,
  onCreateModule,
  onModuleClick,
  onMove
}) => {
  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeNode>>((props, ref) => {
    const { node, style, dragHandle } = props;
    const [showActions, setShowActions] = useState(false);
    
    return (
      <div 
        style={style} 
        ref={(element) => {
          if (allowDrag && dragHandle) dragHandle(element);
          if (typeof ref === 'function') ref(element);
          else if (ref) ref.current = element;
        }}
        className="flex items-center justify-between py-1 px-2 hover:bg-gray-100 group"
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
        data-id={node.id}
      >
        <div 
          className="flex items-center gap-2 cursor-pointer flex-1"
          onClick={() => {
            if (node.isInternal) {
              node.toggle();
            } else if (node.data.module) {
              onModuleClick(node.data.module);
            }
          }}
        >
          {node.data.isFolder ? (
            <>
              {node.isOpen ? 
                <ChevronDown className="h-4 w-4 text-gray-500" /> : 
                <ChevronRight className="h-4 w-4 text-gray-500" />
              }
              <Folder className="h-4 w-4 text-blue-500" />
            </>
          ) : (
            <>
              <span className="w-4" />
              <File className="h-4 w-4 text-gray-500" />
            </>
          )}
          <span className="text-sm text-gray-700">{node.data.name}</span>
        </div>

        {node.data.isFolder && showActions && (
          <div className="flex gap-1">
            <Button 
              variant="ghost" 
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onCreateFolder(node.id);
              }}
            >
              <FolderPlus className="h-3 w-3" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onCreateModule(node.id);
              }}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>
    );
  });

  Node.displayName = 'Node';

  return (
    <div className="h-screen min-w-64 bg-white border-r flex flex-col">
      <div className="p-2 border-b flex justify-between items-center flex-shrink-0 text-gray-700">
        <span className="font-semibold text-sm">PROJECT</span>
        <div className="flex gap-1">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => onCreateFolder(null)}
          >
            <FolderPlus className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => onCreateModule(null)}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {data.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            No items yet. Click the buttons above to add folders or modules.
          </div>
        ) : (
          <Tree<TreeNode>
            data={data}
            onMove={allowDrag ? onMove : undefined}
            width="100%"
            height={800}
            indent={24}
            rowHeight={32}
            overscanCount={1}
          >
            {Node}
          </Tree>
        )}
      </div>
    </div>
  );
};