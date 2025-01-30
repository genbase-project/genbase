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
import { TreeView, Kit, Module, TreeNode, MoveParams } from '../components/TreeView';
import { useModuleStore } from '../store';
import { 
  DEFAULT_PROJECT_ID, 
  buildTreeFromModules, 
  getNewPath
} from '../lib/tree';

interface LeftSidebarProps {
  initialModules?: Kit[];
}

const API_BASE = 'http://localhost:8000';

const LeftSidebar: React.FC<LeftSidebarProps> = ({ initialModules = [] }) => {
  // Local state
  const [treeData, setTreeData] = useState<TreeNode[]>([]);
  const [kits, setKits] = useState<Kit[]>(initialModules);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false);
  const [selectedKit, setSelectedKit] = useState<Kit | null>(null);
  const [currentParentId, setCurrentParentId] = useState<string | null>(null);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [moduleName, setModuleName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [moduleToRename, setModuleToRename] = useState<{ id: string; name: string } | null>(null);
  const [newModuleName, setNewModuleName] = useState('');
  const [modulePath, setModulePath] = useState('');
  const [pathError, setPathError] = useState('');

  // Global state from Zustand
  const { selectedModuleId, setSelectedModule: setGlobalSelectedModule } = useModuleStore();

  // Toast hook
  const { toast } = useToast();

  // Fetch kits and modules on mount
  useEffect(() => {
    Promise.all([
      fetchKits(),
      fetchModules()
    ]).finally(() => setIsLoading(false));
  }, []);

  const fetchKits = async () => {
    try {
      const response = await fetch(`${API_BASE}/kit`);
      if (!response.ok) throw new Error('Failed to fetch kits');
      const result = await response.json();
      setKits(result.kits);
    } catch (error) {
      console.error('Error fetching modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch available modules",
        variant: "destructive"
      });
    }
  };

  const fetchModules = async () => {
    try {
      const response = await fetch(`${API_BASE}/module/project/${DEFAULT_PROJECT_ID}/list`);
      if (!response.ok) throw new Error('Failed to fetch modules');
      const allModules: Module[] = await response.json();
      setTreeData(buildTreeFromModules(allModules));
    } catch (error) {
      console.error('Error fetching modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch modules",
        variant: "destructive"
      });
    }
  };

  const handleModuleClick = (module: Module) => {
    setGlobalSelectedModule(module);
  };

  const handleCreateModule = (parentId: string | null) => {
    setCurrentParentId(parentId);
    setModuleName('');
    setModulePath('');
    setPathError('');
    setIsDialogOpen(true);
  };

  const validatePath = (path: string): boolean => {
    if (!path) return true; // Empty path is allowed
    const pathRegex = /^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$/;
    return pathRegex.test(path);
  };

  const handlePathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPath = e.target.value;
    setModulePath(newPath);
    
    if (!validatePath(newPath)) {
      setPathError('Path must be alphanumeric segments separated by periods (e.g., segment1.segment2)');
    } else {
      setPathError('');
    }
  };

  const handleRename = (moduleId: string, currentName: string) => {
    setModuleToRename({ id: moduleId, name: currentName });
    setNewModuleName(currentName);
    setIsRenameDialogOpen(true);
  };

  const handleRenameConfirm = async () => {
    if (!moduleToRename || !newModuleName.trim()) return;

    try {
      const moduleId = moduleToRename.id;
      const response = await fetch(`${API_BASE}/module/${moduleId}/name`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newModuleName.trim()
        }),
      });

      if (!response.ok) throw new Error('Failed to rename module');

      toast({
        title: "Success",
        description: "Module renamed successfully"
      });

      await fetchModules();
    } catch (error) {
      console.error('Error renaming module:', error);
      toast({
        title: "Error",
        description: "Failed to rename module",
        variant: "destructive"
      });
    } finally {
      setIsRenameDialogOpen(false);
      setModuleToRename(null);
      setNewModuleName('');
    }
  };

  const createModule = async (
    moduleId: string,
    version: string,
    owner: string,
    envVars: Record<string, string>,
    path: string,
    moduleName: string
  ) => {
    try {
      const response = await fetch(`${API_BASE}/module`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: DEFAULT_PROJECT_ID,
          kit_id: moduleId,
          version: version,
          owner: owner,
          env_vars: envVars,
          path: path,
          module_name: moduleName
        }),
      });

      if (!response.ok) throw new Error('Failed to create module');
      
      const result = await response.json();
      toast({
        title: "Success",
        description: "Module created successfully"
      });
      return result;
    } catch (error) {
      console.error('Error creating module:', error);
      toast({
        title: "Error",
        description: "Failed to create module",
        variant: "destructive"
      });
      return null;
    }
  };

  const handleCreateConfirm = async () => {
    if (!selectedKit || !moduleName.trim()) return;
    if (!validatePath(modulePath)) return;

    try {
      const finalPath = modulePath || (currentParentId ? 
        getNewPath(treeData, '', currentParentId, 0) : 
        'root');

      const moduleData = await createModule(
        selectedKit.kit_id,
        selectedKit.version,
        selectedKit.owner,
        envVars,
        finalPath,
        moduleName.trim()
      );

      if (moduleData) {
        await fetchModules();
      }
    } finally {
      setIsDialogOpen(false);
      setSelectedKit(null);
      setEnvVars({});
      setModuleName('');
      setModulePath('');
      setPathError('');
    }
  };

  const updateModulePath = async (moduleId: string, newPath: string) => {
    try {
      const response = await fetch(`${API_BASE}/module/${moduleId}/path`, {
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
      const newPath = getNewPath(treeData, dragIds[0], parentId, index);

      for (const dragId of dragIds) {
        if (dragId.startsWith('module-')) {
          const moduleId = dragId.replace('module-', '');
          await updateModulePath(moduleId, newPath);
        }
      }

      await fetchModules();
    } catch (error) {
      await fetchModules();
    }
  };

  return (
    <>
      <TreeView
        data={treeData}
        modules={kits}
        allowDrag={true}
        onCreateModule={handleCreateModule}
        onModuleClick={handleModuleClick}
        onMove={handleMove}
        onRename={handleRename}
        isLoading={isLoading}
        selectedModuleId={selectedModuleId}
      />

      {/* Create Module Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Create Module Instance</DialogTitle>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Select Module</Label>
              <Select
                value={selectedKit?.name || ''}
                onValueChange={(value) => {
                  const module = kits.find(m => m.name === value);
                  setSelectedKit(module || null);
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
                  {kits.map((module) => (
                    <SelectItem key={module.name} value={module.name}>
                      {module.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label>Module Name</Label>
              <Input
                type="text"
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                placeholder="Enter module name"
              />
            </div>

            <div className="grid gap-2">
              <Label>Module Path (Optional)</Label>
              <Input
                type="text"
                value={modulePath}
                onChange={handlePathChange}
                placeholder="e.g., segment1.segment2"
              />
              {pathError && (
                <span className="text-sm text-red-500">{pathError}</span>
              )}
            </div>

            {selectedKit && (
              <div className="grid gap-4">
                <h4 className="font-medium">Environment Variables</h4>
                {selectedKit.environment.map((env: any) => (
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
              disabled={
                !selectedKit || 
                !moduleName.trim() || 
                // Object.keys(envVars).length === 0 ||
                !!pathError
              }
            >
              Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Rename Dialog */}
      <Dialog open={isRenameDialogOpen} onOpenChange={setIsRenameDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Rename Module</DialogTitle>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>New Name</Label>
              <Input
                type="text"
                value={newModuleName}
                onChange={(e) => setNewModuleName(e.target.value)}
                placeholder="Enter new name"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsRenameDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleRenameConfirm}
              disabled={!newModuleName.trim() || newModuleName === moduleToRename?.name}
            >
              Rename
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default LeftSidebar;