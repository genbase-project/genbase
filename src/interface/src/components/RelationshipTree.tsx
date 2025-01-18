import React from 'react';
import { TreeView } from './TreeView';
import { RuntimeModule, TreeNode } from './TreeView';
import { buildTreeFromModules } from '../lib/tree';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface RelationshipTreeProps {
  modules: RuntimeModule[];
  title: string;
  isLoading?: boolean;
  onAddRelation?: (targetModule: RuntimeModule) => void;
  availableModules?: RuntimeModule[];
}

export const RelationshipTree: React.FC<RelationshipTreeProps> = ({
  modules,
  title,
  isLoading = false,
  onAddRelation,
  availableModules = []
}) => {
  const treeData = buildTreeFromModules(modules);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <span className="text-sm font-medium">{title}</span>
        {onAddRelation && (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Plus className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add {title}</DialogTitle>
              </DialogHeader>
              <div className="max-h-96 overflow-auto">
                {availableModules.map(module => (
                  <div
                    key={module.id}
                    className="flex items-center justify-between p-2 hover:bg-accent rounded-md cursor-pointer"
                    onClick={() => onAddRelation(module)}
                  >
                    <span className="text-sm">{module.module_id}</span>
                    <span className="text-xs text-muted-foreground">{module.path}</span>
                  </div>
                ))}
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>
      <div className="flex-1">
        <TreeView
          data={treeData}
          modules={[]}
          allowDrag={false}
          onModuleClick={() => {}}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};