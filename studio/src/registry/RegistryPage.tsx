import React, { useState, useEffect } from 'react';
import { Download, ExternalLink, ChevronRight, AlertCircle, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';

// Define types based on the kit structure
interface KitEnvironmentVar {
  name: string;
  default?: string;
  optional?: boolean;
}

interface KitAction {
  path: string;
  name: string;
  description: string;
}

interface KitWorkflow {
  agent?: string;
  instruction: string;
  actions?: KitAction[];
  allow_multiple?: boolean;
}

interface KitInstruction {
  name: string;
  path: string;
  description: string;
}

interface KitWorkspaceFile {
  path: string;
  description: string;
}

interface KitPort {
  name: string;
  port: number;
}

interface KitAgent {
  name: string;
  class: string;
  description: string;
}

export interface RegistryKitConfig {
  environment?: KitEnvironmentVar[];
  dependencies?: string[];
  docVersion: string;
  id: string;
  version: string;
  name: string;
  description?: string;
  owner: string;
  agents?: KitAgent[];
  instructions?: {
    specification?: KitInstruction[];
    documentation?: KitInstruction[];
  };
  workflows?: Record<string, KitWorkflow>;
  image?: string;
  workspace?: {
    files?: KitWorkspaceFile[];
    ignote?: string[]; // Assuming this is a typo in the original data and should be "ignore"
  };
  ports?: KitPort[];
}

export interface RegistryKit {
  fileName: string;
  downloadURL: string;
  checksum: string;
  kitConfig: RegistryKitConfig;
  uploadedAt: string;
}

interface RegistryPageProps {
  selectedKit: RegistryKit | null;
}

const RegistryPage: React.FC<RegistryPageProps> = ({ selectedKit }) => {
  const { toast } = useToast();
  const [isInstalling, setIsInstalling] = useState(false);
  const [availableVersions, setAvailableVersions] = useState<string[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>("");

  // Fetch available versions for a kit
  const fetchVersions = async (owner: string, kitId: string) => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit/registry/versions/${owner}/${kitId}`);
      if (!response.ok) throw new Error('Failed to fetch kit versions');
      
      const data = await response.json();
      if (data && Array.isArray(data.versions)) {
        setAvailableVersions(data.versions);
        // Set current version as default
        if (selectedKit?.kitConfig.version) {
          setSelectedVersion(selectedKit.kitConfig.version);
        } else if (data.versions.length > 0) {
          setSelectedVersion(data.versions[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching kit versions:', error);
      // Fallback to using the current version only
      if (selectedKit?.kitConfig.version) {
        setAvailableVersions([selectedKit.kitConfig.version]);
        setSelectedVersion(selectedKit.kitConfig.version);
      }
    }
  };

  // Effect to fetch versions when selected kit changes
  useEffect(() => {
    if (selectedKit) {
      fetchVersions(selectedKit.kitConfig.owner, selectedKit.kitConfig.id);
    }
  }, [selectedKit]);

  const installKit = async (owner: string, kitId: string, version?: string) => {
    setIsInstalling(true);
    try {
      // Use the selected version from dropdown if available, otherwise fallback to passed version
      const versionToInstall = selectedVersion || version;
      const endpoint = versionToInstall 
        ? `${ENGINE_BASE_URL}/kit/install/${owner}/${kitId}/${versionToInstall}`
        : `${ENGINE_BASE_URL}/kit/install/${owner}/${kitId}`;
        
      const response = await fetchWithAuth(endpoint, {
        method: 'POST',
      });
      
      if (!response.ok) throw new Error('Failed to install kit');
      
      toast({
        title: "Success",
        description: `Successfully installed ${kitId} ${versionToInstall ? `(v${versionToInstall})` : ''}`,
      });
    } catch (error) {
      console.error('Error installing kit:', error);
      toast({
        title: "Error",
        description: "Failed to install kit",
        variant: "destructive"
      });
    } finally {
      setIsInstalling(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  if (!selectedKit) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="text-center space-y-4">
          <AlertCircle size={48} className="mx-auto text-gray-400" />
          <h2 className="text-2xl font-semibold text-gray-800">No Kit Selected</h2>
          <p className="text-gray-600 max-w-md">
            Please select a kit from the registry sidebar to view its details.
          </p>
        </div>
      </div>
    );
  }

  const { kitConfig } = selectedKit;

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 backdrop-blur-sm bg-white/50">
        <div className="flex flex-col md:flex-row justify-between items-start gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{kitConfig.name}</h1>
            <div className="flex items-center mt-1 text-gray-600">
              <span className="font-medium">{kitConfig.owner}</span>
              <span className="mx-2">•</span>
              <Badge variant="outline" className="bg-white text-gray-700 border-gray-300">
                v{kitConfig.version}
              </Badge>
              <span className="mx-2">•</span>
              <span className="text-gray-500">Uploaded on {formatDate(selectedKit.uploadedAt)}</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Select
              value={selectedVersion}
              onValueChange={setSelectedVersion}
              disabled={isInstalling || availableVersions.length <= 1}
            >
              <SelectTrigger className="w-32 bg-white border-gray-200 text-gray-800">
                <SelectValue placeholder="Version" />
              </SelectTrigger>
              <SelectContent className="bg-white border-gray-200">
                {availableVersions.map((version) => (
                  <SelectItem key={version} value={version} className="text-gray-800">
                    v{version}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              onClick={() => installKit(kitConfig.owner, kitConfig.id)}
              disabled={isInstalling}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isInstalling ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Installing...
                </span>
              ) : (
                <span className="flex items-center">
                  <Download size={16} className="mr-2" />
                  Install Kit
                </span>
              )}
            </Button>
          </div>
        </div>
        
        {kitConfig.description && (
          <p className="text-gray-700 mt-4 max-w-3xl">{kitConfig.description}</p>
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-6">
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="bg-gray-100 border-gray-200">
                <TabsTrigger value="overview" className="data-[state=active]:bg-white data-[state=active]:text-blue-600">Overview</TabsTrigger>
                {kitConfig.workflows && Object.keys(kitConfig.workflows).length > 0 && (
                  <TabsTrigger value="workflows" className="data-[state=active]:bg-white data-[state=active]:text-blue-600">Workflows</TabsTrigger>
                )}
                {kitConfig.workspace?.files && kitConfig.workspace.files.length > 0 && (
                  <TabsTrigger value="workspace" className="data-[state=active]:bg-white data-[state=active]:text-blue-600">Workspace</TabsTrigger>
                )}
                {kitConfig.instructions && (
                  <TabsTrigger value="documentation" className="data-[state=active]:bg-white data-[state=active]:text-blue-600">Documentation</TabsTrigger>
                )}
              </TabsList>
              
              <TabsContent value="overview" className="mt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Agents */}
                  {kitConfig.agents && kitConfig.agents.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Agents</h3>
                      </div>
                      <div className="bg-white p-4 space-y-3">
                        {kitConfig.agents.map((agent, index) => (
                          <div key={index} className="space-y-1">
                            <h4 className="text-sm text-gray-700 font-medium">{agent.name}</h4>
                            <p className="text-xs text-gray-600">{agent.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Dependencies */}
                  {kitConfig.dependencies && kitConfig.dependencies.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Dependencies</h3>
                      </div>
                      <div className="bg-white p-4">
                        <div className="flex flex-wrap gap-2">
                          {kitConfig.dependencies.map((dep, index) => (
                            <Badge key={index} variant="outline" className="bg-gray-50 border-gray-300 text-gray-700">
                              {dep}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Environment Variables */}
                  {kitConfig.environment && kitConfig.environment.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Environment Variables</h3>
                      </div>
                      <div className="bg-white divide-y divide-gray-200">
                        {kitConfig.environment.map((env, index) => (
                          <div key={index} className="p-3 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-gray-700">{env.name}</span>
                              {env.optional && (
                                <Badge variant="outline" className="text-xs bg-gray-50 border-gray-300 text-gray-600">
                                  Optional
                                </Badge>
                              )}
                            </div>
                            {env.default !== undefined && (
                              <p className="text-xs text-gray-500">Default: {env.default}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Ports */}
                  {kitConfig.ports && kitConfig.ports.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Exposed Ports</h3>
                      </div>
                      <div className="bg-white divide-y divide-gray-200">
                        {kitConfig.ports.map((port, index) => (
                          <div key={index} className="p-3 flex justify-between items-center">
                            <span className="text-sm text-gray-700">{port.name}</span>
                            <Badge className="bg-gray-100 text-gray-800">
                              {port.port}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>
              
              <TabsContent value="workflows" className="mt-6">
                <div className="rounded-md border border-gray-200 overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <h3 className="font-medium text-gray-800">Available Workflows</h3>
                  </div>
                  <div className="bg-white divide-y divide-gray-200">
                    {kitConfig.workflows && Object.entries(kitConfig.workflows).map(([name, workflow], index) => (
                      <div key={index} className="p-4 space-y-3">
                        <h4 className="text-md font-medium text-gray-800">{name}</h4>
                        
                        {workflow.agent && (
                          <div className="text-sm text-gray-600 flex items-center gap-1">
                            <span>Agent:</span>
                            <Badge variant="outline" className="bg-gray-50 border-gray-300 text-gray-700">
                              {workflow.agent}
                            </Badge>
                          </div>
                        )}
                        
                        <div className="text-sm text-gray-600">
                          <span>Instruction: </span>
                          <span className="font-mono text-gray-700">{workflow.instruction}</span>
                        </div>
                        
                        {workflow.actions && workflow.actions.length > 0 && (
                          <div className="space-y-2">
                            <h5 className="text-sm font-medium text-gray-700">Actions:</h5>
                            <div className="space-y-3 pl-3">
                              {workflow.actions.map((action, idx) => (
                                <div key={idx} className="bg-gray-50 p-3 rounded-md">
                                  <h6 className="text-sm font-medium text-gray-800">{action.name}</h6>
                                  <p className="text-xs text-gray-600 mt-1">{action.description}</p>
                                  <p className="text-xs font-mono text-gray-500 mt-1">{action.path}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="workspace" className="mt-6">
                <div className="rounded-md border border-gray-200 overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <h3 className="font-medium text-gray-800">Workspace Files</h3>
                  </div>
                  <div className="bg-white divide-y divide-gray-200">
                    {kitConfig.workspace?.files?.map((file, index) => (
                      <div key={index} className="p-3 space-y-1">
                        <p className="text-sm font-mono text-gray-700 break-all">{file.path}</p>
                        {file.description && (
                          <p className="text-xs text-gray-500">{file.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="documentation" className="mt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Documentation */}
                  {kitConfig.instructions?.documentation && kitConfig.instructions.documentation.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Documentation</h3>
                      </div>
                      <div className="bg-white divide-y divide-gray-200">
                        {kitConfig.instructions.documentation.map((instruction, index) => (
                          <div key={index} className="p-3 space-y-1">
                            <h4 className="text-sm font-medium text-gray-700">{instruction.name}</h4>
                            <p className="text-xs text-gray-500">{instruction.description}</p>
                            <p className="text-xs text-gray-600 font-mono">{instruction.path}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Specifications */}
                  {kitConfig.instructions?.specification && kitConfig.instructions.specification.length > 0 && (
                    <div className="rounded-md border border-gray-200 overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="font-medium text-gray-800">Specifications</h3>
                      </div>
                      <div className="bg-white divide-y divide-gray-200">
                        {kitConfig.instructions.specification.map((instruction, index) => (
                          <div key={index} className="p-3 space-y-1">
                            <h4 className="text-sm font-medium text-gray-700">{instruction.name}</h4>
                            <p className="text-xs text-gray-500">{instruction.description}</p>
                            <p className="text-xs text-gray-600 font-mono">{instruction.path}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default RegistryPage;