import React, { useState, useEffect } from 'react';
import { Sidebar } from "lucide-react";
import { useToast } from '@/hooks/use-toast';
import { Kit } from '../components/TreeView';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
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
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

import SidebarNav from '../SidebarNav';
import ModuleExplorer from '../module/ModuleExplorer';
import RegistryExplorer from '../registry/RegistryExplorer';

interface LeftSidebarProps {
  initialModules?: Kit[];
  onExpand: (expand: boolean) => void;
  expanded: boolean;
  onTabChange?: (tabId: string) => void;
}

const LeftSidebar: React.FC<LeftSidebarProps> = ({ 
  initialModules = [], 
  onExpand, 
  expanded, 
  onTabChange 
}) => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<string>("modules");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<Record<string, string[]>>({});
  const [currentModel, setCurrentModel] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [kits, setKits] = useState<Kit[]>(initialModules);

  // Handle logout function
  const handleLogout = () => {
    localStorage.removeItem('auth_credentials');
    window.location.reload();
  };

  useEffect(() => {
    fetchKits();
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

  // Fetch models on mount
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

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    if (onTabChange) {
      onTabChange(tabId);
    }
  };

  // Render sidebar content based on expanded state and active tab
  const renderSidebarContent = () => {
    if (!expanded) {
      return null;
    }

    // Common wrapper with width constraints and overflow control
    return (
      <div className="h-full flex-1 overflow-hidden border-r border-gray-800">
        {activeTab === "modules" ? (
          <ModuleExplorer initialModules={kits} onCollapse={() => onExpand(false)} />
        ) : activeTab === "registry" ? (
          <RegistryExplorer onCollapse={() => onExpand(false)} />
        ) : (
          <div className="flex flex-col h-full">
            <div className="px-3 py-4 flex justify-between items-center backdrop-blur-sm bg-neutral-900/50 border-b border-gray-800">
              <h2 className="text-lg font-medium text-gray-200">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onExpand(false)}
                className="h-8 w-8 rounded-md hover:bg-neutral-800/70 hover:text-gray-100 text-gray-400"
              >
                <Sidebar size={16} />
              </Button>
            </div>
            <div className="p-4 flex-1 flex flex-col items-center justify-center">
              <div className="text-center space-y-4 max-w-xs">
                <h3 className="text-xl font-semibold text-gray-200">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h3>
                <p className="text-gray-400 text-sm">
                  This section is currently under development.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-row bg-neutral-950 w-full overflow-hidden">
      <SidebarNav 
        onTabChange={handleTabChange} 
        activeTab={activeTab} 
        onExpand={onExpand} 
        onSettingsOpen={() => setIsSettingsOpen(true)} 
        onLogout={handleLogout} 
      />
      
      {renderSidebarContent()}

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
    </div>
  );
};

export default LeftSidebar;