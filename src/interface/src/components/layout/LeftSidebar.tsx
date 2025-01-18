import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from '@/hooks/use-toast';
import { TreeView, Module, RuntimeModule, TreeNode, MoveParams } from '../TreeView';
import { useRuntimeModuleStore } from '../../store';
import { 
  DEFAULT_PROJECT_ID, 
  buildTreeFromModules, 
  getNewPath
} from '../../lib/tree';

interface LeftSidebarProps {
  initialModules?: Module[];
}

const API_BASE = 'http://localhost:8000';

const LeftSidebar: React.FC<LeftSidebarProps> = ({ initialModules = [] }) => {
  // Local state
  const [treeData, setTreeData] = useState<TreeNode[]>([]);
  const [modules, setModules] = useState<Module[]>(initialModules);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState<Module | null>(null);
  const [currentParentId, setCurrentParentId] = useState<string | null>(null);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);

  // Global state from Zustand
  const { selectedModuleId, setSelectedModule: setGlobalSelectedModule } = useRuntimeModuleStore();

  // Toast hook
  const { toast } = useToast();

  // Fetch modules and runtime modules on mount
  useEffect(() => {
    Promise.all([
      fetchModules(),
      fetchRuntimeModules()
    ]).finally(() => setIsLoading(false));
  }, []);

  const fetchModules = async () => {
    try {
      const response = await fetch(`${API_BASE}/module`);
      if (!response.ok) throw new Error('Failed to fetch modules');
      const result = await response.json();
      setModules(result.modules);
    } catch (error) {
      console.error('Error fetching modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch available modules",
        variant: "destructive"
      });
    }
  };

  const fetchRuntimeModules = async () => {
    try {
      const response = await fetch(`${API_BASE}/runtime/project/${DEFAULT_PROJECT_ID}/modules`);
      if (!response.ok) throw new Error('Failed to fetch runtime modules');
      const runtimeModules: RuntimeModule[] = await response.json();
      setTreeData(buildTreeFromModules(runtimeModules));
    } catch (error) {
      console.error('Error fetching runtime modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch runtime modules",
        variant: "destructive"
      });
    }
  };

  const handleModuleClick = (runtimeModule: RuntimeModule) => {
    setGlobalSelectedModule(runtimeModule);
  };

  const handleCreateModule = (parentId: string | null) => {
    setCurrentParentId(parentId);
    setIsDialogOpen(true);
  };

  const createRuntimeModule = async (
    moduleId: string,
    version: string,
    owner: string,
    envVars: Record<string, string>,
    path: string
  ) => {
    try {
      const response = await fetch(`${API_BASE}/runtime/module`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: DEFAULT_PROJECT_ID,
          module_id: moduleId,
          version: version,
          owner: owner,
          env_vars: envVars,
          path: path
        }),
      });

      if (!response.ok) throw new Error('Failed to create runtime module');
      
      const result = await response.json();
      toast({
        title: "Success",
        description: "Runtime module created successfully"
      });
      return result;
    } catch (error) {
      console.error('Error creating runtime module:', error);
      toast({
        title: "Error",
        description: "Failed to create runtime module",
        variant: "destructive"
      });
      return null;
    }
  };

  const handleCreateConfirm = async () => {
    if (!selectedModule) return;

    try {
      // Get the path based on current folder structure
      const path = currentParentId ? 
        getNewPath(treeData, '', currentParentId, 0) : 
        'root';

      const runtimeModule = await createRuntimeModule(
        selectedModule.module_id,
        selectedModule.version,
        selectedModule.owner,
        envVars,
        path
      );

      if (runtimeModule) {
        // Refresh the tree to show the new module
        await fetchRuntimeModules();
      }
    } finally {
      setIsDialogOpen(false);
      setSelectedModule(null);
      setEnvVars({});
    }
  };

  const updateModulePath = async (runtimeId: string, newPath: string) => {
    try {
      const response = await fetch(`${API_BASE}/runtime/module/${runtimeId}/path`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: DEFAULT_PROJECT_ID,
          path: newPath
        }),
      });

      if (!response.ok) throw new Error('Failed to update module path');

      toast({
        title: "Success",
        description: "Module path updated successfully"
      });
    } catch (error) {
      console.error('Error updating module path:', error);
      toast({
        title: "Error",
        description: "Failed to update module path",
        variant: "destructive"
      });
      throw error;
    }
  };

  const handleMove = async (params: MoveParams) => {
    const { dragIds, parentId, index } = params;

    try {
      // Calculate new path based on target location
      const newPath = getNewPath(treeData, dragIds[0], parentId, index);

      // Update the path for each dragged module
      for (const dragId of dragIds) {
        if (dragId.startsWith('runtime-')) {
          const runtimeId = dragId.replace('runtime-', '');
          await updateModulePath(runtimeId, newPath);
        }
      }

      // Refresh the tree to show updated structure
      await fetchRuntimeModules();
    } catch (error) {
      // If there's an error, refresh the tree to restore the original state
      await fetchRuntimeModules();
    }
  };

  return (
    <>
      <TreeView
        data={treeData}
        modules={modules}
        allowDrag={true}
        onCreateModule={handleCreateModule}
        onModuleClick={handleModuleClick}
        onMove={handleMove}
        isLoading={isLoading}
        selectedModuleId={selectedModuleId}
      />

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Create Runtime Module Instance</DialogTitle>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Select Module</Label>
              <Select
                value={selectedModule?.name || ''}
                onValueChange={(value) => {
                  const module = modules.find(m => m.name === value);
                  setSelectedModule(module || null);
                  if (module) {
                    const initialEnvVars: Record<string, string> = {};
                    module.environment.forEach((env: any) => {
                      if (env.default !== undefined) {
                        initialEnvVars[env.name] = String(env.default);
                      }
                    });
                    setEnvVars(initialEnvVars);
                  }
                }}
              >
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
            </div>

            {selectedModule && (
              <div className="grid gap-4">
                <h4 className="font-medium">Environment Variables</h4>
                {selectedModule.environment.map((env: any) => (
                  <div key={env.name} className="grid gap-2">
                    <Label>
                      {env.name}
                      {env.optional && ' (Optional)'}
                    </Label>
                    <Input
                      type="text"
                      value={envVars[env.name] || ''}
                      onChange={(e) => setEnvVars(prev => ({
                        ...prev,
                        [env.name]: e.target.value
                      }))}
                      placeholder={env.default !== undefined ? String(env.default) : ''}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleCreateConfirm}
              disabled={!selectedModule || Object.keys(envVars).length === 0}
            >
              Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default LeftSidebar;