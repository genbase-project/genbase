import React, { useState, useEffect } from 'react';
import { Sidebar, SidebarClose, Settings, LogOut } from "lucide-react";
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
import {
DialogFooter,
DialogDescription,
} from "@/components/ui/dialog"
import { SidebarHeader } from '@/components/ui/sidebar';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
interface LeftSidebarProps {
  initialModules?: Kit[];
  onExpand:  (expand: boolean) => void;
  expanded: boolean
}


const LeftSidebar: React.FC<LeftSidebarProps> = ({ initialModules = [], onExpand: onExpand, expanded  }) => {
  // Add handleLogout function
  const handleLogout = () => {
    localStorage.removeItem('auth_credentials');
    window.location.reload();
  };

const { toast } = useToast();
const { selectedModuleId, setSelectedModule } = useModuleStore();

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
const [isSettingsOpen, setIsSettingsOpen] = useState(false);
const [availableModels, setAvailableModels] = useState<Record<string, string[]>>({});
const [currentModel, setCurrentModel] = useState<string>('');






useEffect(() => {
  Promise.all([
    fetchKits(),
    fetchModules()
  ]).finally(() => setIsLoading(false));
}, []);

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

// Fetch modules and models on mount
useEffect(() => {
  const fetchModels = async () => {
    try {
      const [availableRes, currentRes] = await Promise.all([
        fetchWithAuth(`${ENGINE_BASE_URL}/model/list`),
        fetchWithAuth(`${ENGINE_BASE_URL}/model/current`)
      ]);
      
      if (availableRes.ok) {
        const models = await availableRes.json();
        setAvailableModels(models);
      }
      
      if (currentRes.ok) {
        const current = await currentRes.json();
        setCurrentModel(current.model_name);
      }
    } catch (error) {
      console.error('Error fetching model data:', error);
    }
  };
  
  fetchModels();
}, []);

const [selectedProvider, setSelectedProvider] = useState<string>('');
const [selectedModel, setSelectedModel] = useState<string>('');

// Set initial values when currentModel changes
useEffect(() => {
  if (currentModel) {
    const provider = Object.keys(availableModels).find(p => 
      availableModels[p].includes(currentModel)
    );
    if (provider) {
      setSelectedProvider(provider);
      setSelectedModel(currentModel);
    }
  }
}, [currentModel, availableModels]);

const handleSaveModelSettings = async () => {
  if (!selectedModel) return;
  
  try {
    const res = await fetchWithAuth(`${ENGINE_BASE_URL}/model/set`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ model_name: selectedModel })
    });
    
    if (res.ok) {
      setCurrentModel(selectedModel);
      toast({
        title: "Success",
        description: "Model settings saved successfully",
        variant: "default"
      });
      setIsSettingsOpen(false);
    } else {
      throw new Error('Failed to update model');
    }
  } catch (error) {
    toast({
      title: "Error",
      description: "Failed to save model settings",
      variant: "destructive"
    });
  }
};








































const fetchModules = async () => {
  try {
    const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/project/${DEFAULT_PROJECT_ID}/list`);
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
    const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module`, {
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
    const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/path`, {
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
    <div className="h-full flex flex-col bg-neutral-950">
      <div className="flex flex-col h-full">
        <SidebarHeader className="px-2 py-4 flex flex-row items-center justify-between backdrop-blur-sm bg-neutral-900/50">
          <div className={expanded ? "flex justify-between items-center w-full" : ''}>
            <div className="flex items-center gap-3 text-xl">
              <img src="/logo.png" alt="Genbase Logo" className="h-10 w-10" />
              {expanded && <span className="font-semibold text-gray-300">Genbase Studio</span>}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  const newIsCollapsed = !expanded;
                  onExpand(newIsCollapsed);
                }}
                className="h-10 w-10 rounded-full hover:bg-neutral-800/70 hover:text-gray-100 transition-colors text-gray-50"
                aria-label={!expanded ? "Expand sidebar" : "Collapse sidebar"}
              >
                {!expanded ? <Sidebar size={16} /> : <Sidebar size={16} />}
              </Button>
            </div>
          </div>
        </SidebarHeader>

        {expanded ? (
          <>
            {/* Main content area with fixed height and proper flex layout */}
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

              <div className="p-2 space-y-2 border-t border-gray-800 mt-auto">
                <Button
                  variant="ghost"
                  onClick={() => setIsSettingsOpen(true)}
                  className="w-full justify-start gap-2 hover:bg-neutral-800/70 hover:text-gray-100 text-gray-300 transition-colors"
                  aria-label="Settings"
                >
                  <Settings size={16} />
                  Settings
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleLogout}
                  className="w-full justify-start gap-2 hover:bg-neutral-800/70 text-red-400 hover:text-red-300 transition-colors"
                  aria-label="Logout"
                >
                  <LogOut size={16} />
                  Logout
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col justify-end">
            <div className="p-2 space-y-2 border-t border-gray-800">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsSettingsOpen(true)}
                className="w-10 h-10 rounded-full hover:bg-neutral-800/70 hover:text-gray-100 text-gray-300 transition-colors"
                aria-label="Settings"
              >
                <Settings size={16} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="w-10 h-10 rounded-full hover:bg-neutral-800/70 text-red-400 hover:text-red-300 transition-colors"
                aria-label="Logout"
              >
                <LogOut size={16} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>


    {/* Create Module Dialog */}
    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
      <DialogContent className="sm:max-w-[425px] bg-neutral-900/95 backdrop-blur-sm shadow-lg border-gray-800">
        <DialogHeader className="space-y-1">
          <DialogTitle className="text-xl text-gray-100">Create Module Instance</DialogTitle>
          <DialogDescription className="text-gray-400">Configure your new module.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4 px-1">
          <div className="grid gap-2">
            <Label className="text-sm font-medium text-gray-300">Select Module</Label>
            <Select
              value={selectedKit?.name || ''}
              onValueChange={(value) => {
                const module = kits.find(m => m.name === value);
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
              <SelectTrigger className="bg-neutral-800 border-gray-700 text-gray-100">
                <SelectValue placeholder="Select a module" className="text-gray-400" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-gray-700">
                {kits.map((module) => (
                  <SelectItem 
                    key={module.name} 
                    value={module.name}
                    className="text-gray-100 hover:bg-neutral-800"
                  >
                    {module.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label className="text-sm font-medium text-gray-300">Module Name</Label>
            <Input
              type="text"
              value={moduleName}
              onChange={(e) => setModuleName(e.target.value)}
              placeholder="Enter module name"
              className="bg-neutral-800/50 border-gray-700 text-gray-100 placeholder:text-gray-500"
            />
          </div>

          <div className="grid gap-2">
            <Label className="text-sm font-medium text-gray-300">Module Path (Optional)</Label>
            <Input
              type="text"
              value={modulePath}
              onChange={handlePathChange}
              placeholder="e.g., segment1.segment2"
              className="bg-neutral-800/50 border-gray-700 text-gray-100 placeholder:text-gray-500"
            />
            {pathError && (
              <span className="text-sm text-red-400">{pathError}</span>
            )}
          </div>

          {selectedKit && (selectedKit.environment?.length > 0) && (
            <div className="grid gap-4">
              <h4 className="font-medium text-gray-300">Environment Variables</h4>
              {selectedKit.environment.map((env: any) => (
                <div key={env.name} className="grid gap-2">
                  <Label className="text-gray-300">
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
                    className="bg-neutral-800/50 border-gray-700 text-gray-100 placeholder:text-gray-500"
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
            className="bg-neutral-800 text-gray-300 hover:bg-neutral-700  border-gray-700"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleCreateConfirm}
            className="bg-neutral-700 hover:bg-neutral-600 text-white"
            disabled={!selectedKit || !moduleName.trim() || !!pathError}
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Rename Dialog */}
    <Dialog open={isRenameDialogOpen} onOpenChange={setIsRenameDialogOpen}>
      <DialogContent className="sm:max-w-[425px] bg-neutral-900/95 backdrop-blur-sm shadow-lg border-gray-800">
        <DialogHeader className="space-y-1">
          <DialogTitle className="text-xl text-gray-100">Rename Module</DialogTitle>
          <DialogDescription className="text-gray-400">Enter a new name for your module.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label className="text-sm font-medium text-gray-300">New Name</Label>
            <Input
              type="text"
              value={newModuleName}
              onChange={(e) => setNewModuleName(e.target.value)}
              placeholder="Enter new name"
              className="bg-neutral-800/50 border-gray-700 text-gray-100 placeholder:text-gray-500"
            />
          </div>
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={() => setIsRenameDialogOpen(false)} 
            className="bg-neutral-800 hover:bg-neutral-700 text-gray-300 border-gray-700"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleRenameConfirm}
            className="bg-neutral-700 hover:bg-neutral-600 text-white"
            disabled={!newModuleName.trim() || newModuleName === moduleToRename?.name}
          >
            Rename
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Settings Dialog */}
    <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
      <DialogContent className="sm:max-w-[500px] bg-neutral-900/95 backdrop-blur-sm shadow-lg border-gray-800">
        <DialogHeader>
          <DialogTitle className="text-xl text-gray-100">Model Settings</DialogTitle>
          <DialogDescription className="text-gray-400">
            Configure the language model for your assistant.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-2">Current Model</h3>
            <div className="text-sm text-gray-400 bg-neutral-800 p-2 rounded-md">
              {currentModel || 'No model selected'}
            </div>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider" className="text-sm font-medium text-gray-300">
                Provider
              </Label>
              <Select
                onValueChange={setSelectedProvider}
                value={selectedProvider}
              >
                <SelectTrigger id="provider" className="bg-neutral-800 border-gray-700 text-gray-100">
                  <SelectValue placeholder="Select provider" className="text-gray-400" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-900 border-gray-700">
                  {Object.keys(availableModels).map((provider) => (
                    <SelectItem 
                      key={provider} 
                      value={provider}
                      className="text-gray-100 hover:bg-neutral-800"
                    >
                      <span className="capitalize">{provider}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model" className="text-sm font-medium text-gray-300">
                Model
              </Label>
              <Select
                value={selectedModel}
                onValueChange={setSelectedModel}
              >
                <SelectTrigger id="model" className="bg-neutral-800 border-gray-700 text-gray-100">
                  <SelectValue placeholder="Select model" className="text-gray-400" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-900 border-gray-700">
                  {availableModels[selectedProvider]?.map((model) => (
                    <SelectItem 
                      key={model} 
                      value={model}
                      className="text-gray-100 hover:bg-neutral-800"
                    >
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter className="space-x-2">
          <Button 
            variant="outline" 
            onClick={() => setIsSettingsOpen(false)}
            className="bg-neutral-800 hover:bg-neutral-700 text-white border-gray-700"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSaveModelSettings}
            disabled={!selectedModel}
            className="bg-neutral-700 hover:bg-neutral-600 text-white"
          >
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </>
);
};

export default LeftSidebar;
