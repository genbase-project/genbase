import { Network, PlugZap, Plug, Plus, ChevronDown, Box, MoreVertical, Search, Download, Upload } from 'lucide-react';
import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { toast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { Textarea } from '@/components/ui/textarea';
import { DEFAULT_PROJECT_ID } from '@/lib/tree';
import { Module } from '@/components/TreeView';
import { AddProvideDialog, ModuleProvide, ProvideRelationshipCard } from './dialog';


// Define ProvideType enum
enum ProvideType {
  WORKSPACE = "workspace",
  ACTION = "action",
}


// Custom hook for managing module provides
export const useModuleProvides = (moduleId: string) => {
  const [providing, setProviding] = useState<ModuleProvide[]>([]);
  const [receiving, setReceiving] = useState<ModuleProvide[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchProviding = useCallback(async () => {
    if (!moduleId) return;
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/providing`);
      const data = await response.json();
      setProviding(data);
    } catch (error) {
      console.error('Error fetching provides:', error);
      toast({
        title: "Error",
        description: "Failed to fetch resources this module is providing",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchReceiving = useCallback(async () => {
    if (!moduleId) return;
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/receiving`);
      const data = await response.json();
      setReceiving(data);
    } catch (error) {
      console.error('Error fetching receives:', error);
      toast({
        title: "Error",
        description: "Failed to fetch resources this module is receiving",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchAvailableModules = useCallback(async () => {
    console.log('Fetching available modules...');
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/project/${DEFAULT_PROJECT_ID}/list`);
      const data = await response.json();
      return data.filter((m: Module) => m.module_id !== moduleId);
    } catch (error) {
      console.error('Error fetching available modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch available modules",
        variant: "destructive"
      });
      return [];
    }
  }, [moduleId]);

  const createProvide = useCallback(async (
    receiverId: string, 
    resourceType: ProvideType, 
    description?: string
  ) => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/provide`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider_id: moduleId,
          receiver_id: receiverId,
          resource_type: resourceType,
          description
        }),
      });

      const data = await response.json();
      
      toast({
        title: "Success",
        description: `${resourceType} resource provision created successfully`
      });
      
      await fetchProviding();
      return data;
    } catch (error) {
      console.error('Error creating provide relationship:', error);
      toast({
        title: "Error",
        description: "Failed to create resource provision",
        variant: "destructive"
      });
      return null;
    }
  }, [moduleId, fetchProviding]);

  const deleteProvide = useCallback(async (
    receiverId: string, 
    resourceType: ProvideType
  ) => {
    try {
      await fetchWithAuth(
        `${ENGINE_BASE_URL}/module/provide/${moduleId}/${receiverId}/${resourceType}`, 
        { method: 'DELETE' }
      );
      
      toast({
        title: "Success",
        description: `${resourceType} resource provision removed successfully`
      });
      
      await fetchProviding();
      return true;
    } catch (error) {
      console.error('Error removing provide relationship:', error);
      toast({
        title: "Error",
        description: "Failed to remove resource provision",
        variant: "destructive"
      });
      return false;
    }
  }, [moduleId, fetchProviding]);

  const updateProvideDescription = useCallback(async (
    receiverId: string,
    resourceType: ProvideType,
    description: string
  ) => {
    try {
      await fetchWithAuth(
        `${ENGINE_BASE_URL}/module/provide/${moduleId}/${receiverId}/${resourceType}/description`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            description
          }),
        }
      );
      
      toast({
        title: "Success",
        description: "Resource provision description updated successfully"
      });
      
      await fetchProviding();
      return true;
    } catch (error) {
      console.error('Error updating provide description:', error);
      toast({
        title: "Error",
        description: "Failed to update resource provision description",
        variant: "destructive"
      });
      return false;
    }
  }, [moduleId, fetchProviding]);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchProviding(),
        fetchReceiving()
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [fetchProviding, fetchReceiving]);

  return {
    providing,
    receiving,
    isLoading,
    fetchAll,
    createProvide,
    deleteProvide,
    updateProvideDescription,
    fetchAvailableModules
  };
};



const ModuleProvideManagement: React.FC<{
  selectedModule?: Module | null;
}> = ({ selectedModule }) => {
  const [availableModules, setAvailableModules] = useState<Module[]>([]);
  const [selectedTab, setSelectedTab] = useState("providing");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [moduleMap, setModuleMap] = useState<Record<string, Module>>({});
  
  const {
    providing,
    receiving,
    isLoading,
    fetchAll,
    createProvide,
    deleteProvide,
    updateProvideDescription,
    fetchAvailableModules
  } = useModuleProvides(selectedModule?.module_id || '');

  useEffect(() => {
    if (selectedModule?.module_id) {
      fetchAll();
    }
  }, [fetchAll, selectedModule?.module_id]);

  useEffect(() => {
    const fetchModules = async () => {
      if (!selectedModule?.module_id) return;
      
      const modules = await fetchAvailableModules();

      console.log('Available modules:', modules);
      if (modules) {
        setAvailableModules(modules);
        
        // Create a map of module IDs to modules
        const map: Record<string, Module> = {};
        modules.forEach((module: Module) => {
          map[module.module_id] = module;
        });
        
        // Add the selected module to the map
        map[selectedModule.module_id] = selectedModule;
        
        setModuleMap(map);
      }
    };

    if (selectedModule?.module_id) {
      fetchModules();
    }
  }, [fetchAvailableModules, selectedModule]);

  const handleAddProvide = async (
    receiverId: string, 
    resourceType: ProvideType, 
    description: string
  ) => {
    if (!selectedModule?.module_id) return null;
    return await createProvide(receiverId, resourceType, description);
  };

  const handleDeleteProvide = async (provide: ModuleProvide) => {
    if (!selectedModule?.module_id) return false;
    return await deleteProvide(
      provide.receiver_id, 
      provide.resource_type as ProvideType
    );
  };

  const handleUpdateDescription = async (provide: ModuleProvide, description: string) => {
    if (!selectedModule?.module_id) return false;
    return await updateProvideDescription(
      provide.receiver_id,
      provide.resource_type as ProvideType,
      description
    );
  };

  if (!selectedModule?.module_id) {
    return (
      <div className="h-full flex">
        <div className="flex flex-col text-center justify-center gap-2 p-2 border-l bg-background">
          <div className="text-center justify-center">
            <Plug className="w-12 h-12 text-gray-400 mb-2 mx-auto" strokeWidth={1.5} />
            
            <h2 className="text-xl font-semibold text-gray-700 mb-2">No Module Selected</h2>
            <p className="text-gray-500">Select a module from the sidebar to manage resource provisions</p>
          </div>
        </div>
      </div>
    );
  }

  const renderProviding = () => {
    if (isLoading) {
      return (
        <div className="p-4 text-center text-muted-foreground">
          Loading...
        </div>
      );
    }

    if (providing.length === 0) {
      return (
        <div className="p-4 text-center text-muted-foreground">
          This module is not providing any resources to other modules
        </div>
      );
    }

    return providing.map((provide) => (
      <ProvideRelationshipCard
        key={`${provide.provider_id}-${provide.receiver_id}-${provide.resource_type}`}
        module={moduleMap[provide.receiver_id]}
        provide={provide}
        onUpdate={(description) => handleUpdateDescription(provide, description)}
        onDelete={() => handleDeleteProvide(provide)}
        isProvider={true}
      />
    ));
  };

  const renderReceiving = () => {
    if (isLoading) {
      return (
        <div className="p-4 text-center text-muted-foreground">
          Loading...
        </div>
      );
    }

    if (receiving.length === 0) {
      return (
        <div className="p-4 text-center text-muted-foreground">
          This module is not receiving any resources from other modules
        </div>
      );
    }

    return receiving.map((provide) => (
      <ProvideRelationshipCard
        key={`${provide.provider_id}-${provide.receiver_id}-${provide.resource_type}`}
        module={moduleMap[provide.provider_id]}
        provide={provide}
        isProvider={false}
      />
    ));
  };

  return (
    <div className="h-full flex border-l">
      <div className="flex-1">
        <Card className="h-full flex flex-col border-none rounded-none">
          <CardHeader className="px-4 py-3 space-y-1">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Resource Provisions</CardTitle>
              <Button 
                variant="outline" 
                size="sm" 
                className="h-8"
                onClick={() => setIsAddDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Provide Resource
              </Button>
            </div>
          </CardHeader>
          
          <CardContent className="p-4 pt-0 flex-1">
            <Tabs 
              defaultValue="providing" 
              value={selectedTab} 
              onValueChange={setSelectedTab}
              className="h-full flex flex-col"
            >
              <TabsList className="grid grid-cols-2 mb-4">
                <TabsTrigger value="providing" className="flex items-center space-x-1">
                  <Upload className="h-4 w-4" />
                  <span>Providing</span>
                </TabsTrigger>
                <TabsTrigger value="receiving" className="flex items-center space-x-1">
                  <Download className="h-4 w-4" />
                  <span>Receiving</span>
                </TabsTrigger>
              </TabsList>
              
              <ScrollArea className="flex-1">
                <TabsContent value="providing" className="mt-0 h-full">
                  {renderProviding()}
                </TabsContent>
                
                <TabsContent value="receiving" className="mt-0 h-full">
                  {renderReceiving()}
                </TabsContent>
              </ScrollArea>
            </Tabs>
          </CardContent>
        </Card>
      </div>
      
      <AddProvideDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        availableModules={availableModules}
        onAddProvide={handleAddProvide}
      />
    </div>
  );
};

export default ModuleProvideManagement;