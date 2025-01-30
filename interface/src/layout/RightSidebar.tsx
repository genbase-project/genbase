import React, { useEffect, useState } from 'react';
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Network, Link2 } from 'lucide-react';
import { RelationshipTree } from '../components/RelationshipTree';
import { useModuleRelationships } from '../hooks/useModuleRelationships';
import { Module } from '../components/TreeView';

interface RightSidebarProps {
  rightTab: string;
  setRightTab: (tab: string) => void;
  selectedModule?: Module | null;
}

const RightSidebar: React.FC<RightSidebarProps> = ({ rightTab, setRightTab, selectedModule }) => {
  const [availableModules, setAvailableModules] = useState<Module[]>([]);
  
  // Always call the hook with a default value
  const {
    context,
    connections,
    isLoading,
    fetchAll,
    createConnection,
    fetchAvailableModules
  } = useModuleRelationships(selectedModule?.module_id || '');

  // Only fetch data when we have a selected module
  useEffect(() => {
    if (selectedModule?.module_id) {
      fetchAll();
    }
  }, [fetchAll, selectedModule?.module_id]);

  useEffect(() => {
    const fetchAndSetAvailableModules = async () => {
      if (!selectedModule?.module_id) return;
      
      const modules = await fetchAvailableModules();
      if (modules) {
        const existingIds = new Set([selectedModule.module_id]);
        let filtered = modules.filter((m: any) => !existingIds.has(m.id));

        if (rightTab === 'context') {
          filtered = filtered.filter((m: any) => 
            !context.some(c => c.module_id === m.id)
          );
        } else if (rightTab === 'connections') {
          filtered = filtered.filter((m: any) => 
            !connections.some((r: { module_id: any; }) => r.module_id === m.id)
          );
        }

        setAvailableModules(filtered);
      }
    };

    if (rightTab && selectedModule?.module_id) {
      fetchAndSetAvailableModules();
    }
  }, [rightTab, context, connections, fetchAvailableModules, selectedModule?.module_id]);

  const handleAddConnection = async (targetModule: Module, type: 'context' | 'connection') => {
    if (!selectedModule?.module_id) return;

    console.log('Module id:', selectedModule);
    
    await createConnection(targetModule.module_id, type);
    const newAvailable = availableModules.filter(m => m.module_id !== targetModule.module_id);
    setAvailableModules(newAvailable);
  };

  // Return empty div if no module is selected
  if (!selectedModule?.module_id) {
    return <div className="h-full flex">
      <div className="flex flex-col gap-2 p-2 border-l bg-background">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" disabled>
                <Network className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Context</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" disabled>
                <Link2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Connections</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>;
  }

  return (
    <div className="h-full flex">
      {rightTab && (
        <div 
          className="flex-1 border-l hover:overflow-overlay"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgb(209 213 219 / 0.4) transparent'
          }}
        >
          {rightTab === 'context' && (
            <RelationshipTree
              modules={context}
              title="Context"
              isLoading={isLoading}
              onAddRelation={(module) => handleAddConnection(module, 'context')}
              availableModules={availableModules}
            />
          )}
          {rightTab === 'connections' && (
            <RelationshipTree
              modules={connections}
              title="Connections"
              isLoading={isLoading}
              onAddRelation={(module) => handleAddConnection(module, 'connection')}
              availableModules={availableModules}
            />
          )}
        </div>
      )}

      <div className="flex flex-col gap-2 p-2 border-l bg-background">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'context' ? 'bg-gray-100' : ''}
                onClick={() => setRightTab('context')}
              >
                <Network className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Context</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'connections' ? 'bg-gray-100' : ''}
                onClick={() => setRightTab('connections')}
              >
                <Link2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Connections</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
};

export default RightSidebar;