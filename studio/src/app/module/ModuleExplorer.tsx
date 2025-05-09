import React, { useState, useEffect } from 'react';
import { Sidebar, SidebarClose } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
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
import { TreeView, Kit, Module, TreeNode, MoveParams } from '../../components/TreeView';
import { useModuleStore } from '../../stores/store';
import {
  DEFAULT_PROJECT_ID,
  buildTreeFromModules,
  getNewPath
} from '../../lib/tree';
import { SidebarHeader } from '@/components/ui/sidebar';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { ProjectSelector } from '@/app/module/ProjectSelector';
import { useProjectStore } from '@/stores/projectStore';

interface ModuleExplorerProps {
  initialModules?: Kit[];
  onCollapse: () => void;
}

const ModuleExplorer: React.FC<ModuleExplorerProps> = ({ initialModules = [], onCollapse }) => {
  const { toast } = useToast();
  const { selectedModuleId, setSelectedModule } = useModuleStore();
  const { selectedProjectId, setSelectedProject } = useProjectStore();

  const handleModuleClick = (module: Module) => {
    setSelectedModule(module);
  };

  const handleCreateModule = async (parentId: string | null) => {
    setCurrentParentId(parentId);
    setModuleName('');
    setModulePath('');
    setPathError('');
    setIsDialogOpen(true);
  };

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

  // Set default project on component mount if none is selected
  useEffect(() => {
    if (!selectedProjectId) {
      setSelectedProject(DEFAULT_PROJECT_ID);
    }
  }, [selectedProjectId, setSelectedProject]);

  useEffect(() => {
    fetchKits();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      setIsLoading(true);
      fetchModules().finally(() => setIsLoading(false));
    }
  }, [selectedProjectId]);

  const fetchKits = async () => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit`);
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
      // Only use selectedProjectId since we ensure it's set to DEFAULT_PROJECT_ID initially
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/project/${selectedProjectId}/list`);
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
      const moduleId = (moduleToRename.id).replace('module-', '');
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/name`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newModuleName.trim(),
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
      // Use the currently selected project ID
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: selectedProjectId,
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
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/path`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: selectedProjectId,
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
      <div className="flex flex-col h-full">
        <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm bg-neutral-50">
          <div className="flex flex-row items-center space-x-4">
            <h2 className="text-lg font-medium">Modules</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onCollapse}
            className="h-8 w-8 rounded-md hover:bg-neutral-50"
            aria-label="Collapse sidebar"
          >
            <Sidebar size={16} />
          </Button>
        </SidebarHeader>

        {/* Project Selector Component */}
        <ProjectSelector />

        <div className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 overflow-hidden">
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
          </div>
        </div>
      </div>

      {/* Create Module Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px] bg-neutral-50 backdrop-blur-sm shadow-lg">
          <DialogHeader className="space-y-1">
            <DialogTitle className="text-xl text-gray-800">Create Module</DialogTitle>
            <DialogDescription className="text-gray-700">Configure your new module.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 px-1">
            <div className="grid gap-2">
              <Label className="text-sm font-medium text-gray-800">Select Module</Label>
              <Select
                value={selectedKit ? `${selectedKit.name}|${selectedKit.owner}|${selectedKit.version}` : ""}
                onValueChange={(value) => {
                  const [name, owner, version] = value.split('|');
                  const module = kits.find(m => 
                    m.name === name && 
                    m.owner === owner && 
                    m.version === version
                  );
                  
                  setSelectedKit(module || null);
                  if (module) {
                    const initialEnvVars: Record<string, string> = {};
                    module.environment?.forEach((env: any) => {
                      if (env.default !== undefined) {
                        initialEnvVars[env.name] = String(env.default);
                      }
                    });
                    setEnvVars(initialEnvVars);
                  }
                }}
              >
                <SelectTrigger className="bg-neutral-50">
                  <SelectValue placeholder="Select a module" className="" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-50">
                  {kits.map((module) => (
                    <SelectItem 
                      key={`${module.name}|${module.owner}|${module.version}`}
                      value={`${module.name}|${module.owner}|${module.version}`}
                      className="hover:bg-neutral-50"
                    >
                      {module.name} ({module.owner}) {module.version}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label className="text-sm font-medium">Module Name</Label>
              <Input
                type="text"
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                placeholder="Enter module name"
                className="bg-neutral-50 placeholder:text-gray-500"
              />
            </div>

            <div className="grid gap-2">
              <Label className="text-sm font-medium">Module Path (Optional)</Label>
              <Input
                type="text"
                value={modulePath}
                onChange={handlePathChange}
                placeholder="e.g., segment1.segment2"
                className="bg-neutral-50 placeholder:text-gray-500"
              />
              {pathError && (
                <span className="text-sm text-red-400">{pathError}</span>
              )}
            </div>

            {selectedKit && (selectedKit.environment?.length > 0) && (
              <div className="grid gap-4">
                <h4 className="font-medium">Environment Variables</h4>
                {selectedKit.environment.map((env: any) => (
                  <div key={env.name} className="grid gap-2">
                    <Label className="">
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
                      className="placeholder:text-gray-500"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsDialogOpen(false)} 
              className="bg-neutral-50 hover:bg-neutral-100"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateConfirm}
              className="bg-neutral-700 hover:bg-neutral-800"
              disabled={!selectedKit || !moduleName.trim() || !!pathError}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename Dialog */}
      <Dialog open={isRenameDialogOpen} onOpenChange={setIsRenameDialogOpen}>
        <DialogContent className="sm:max-w-[425px] bg-neutral-50 backdrop-blur-sm shadow-lg">
          <DialogHeader className="space-y-1">
            <DialogTitle className="text-xl text-gray-900">Rename Module</DialogTitle>
            <DialogDescription className="text-gray-700">Enter a new name for your module.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label className="text-sm font-medium text-gray-700">New Name</Label>
              <Input
                type="text"
                value={newModuleName}
                onChange={(e) => setNewModuleName(e.target.value)}
                placeholder="Enter new name"
                className="bg-neutral-50 text-gray-700 placeholder:text-gray-500"
              />
            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsRenameDialogOpen(false)} 
              className=""
            >
              Cancel
            </Button>
            <Button 
              onClick={handleRenameConfirm}
              className="bg-neutral-700 hover:bg-neutral-800 text-white"
              disabled={!newModuleName.trim() || newModuleName === moduleToRename?.name}
            >
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ModuleExplorer;