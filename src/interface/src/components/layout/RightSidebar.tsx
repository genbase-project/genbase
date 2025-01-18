import React, { useEffect, useState } from 'react';
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PackageOpen, GitFork, Network } from 'lucide-react';
import { RelationshipTree } from '../RelationshipTree';
import { useModuleRelationships } from '../../hooks/useModuleRelationships';
import { RuntimeModule } from '../TreeView';

interface RightSidebarProps {
  rightTab: string;
  setRightTab: (tab: string) => void;
  selectedModule?: RuntimeModule | null;
}

const RightSidebar: React.FC<RightSidebarProps> = ({ rightTab, setRightTab, selectedModule }) => {
  const [availableModules, setAvailableModules] = useState<RuntimeModule[]>([]);
  
  // Always call the hook with a default value
  const {
    dependencies,
    dependents,
    context,
    isLoading,
    fetchAll,
    createRelation,
    fetchAvailableModules
  } = useModuleRelationships(selectedModule?.id || '');

  // Only fetch data when we have a selected module
  useEffect(() => {
    if (selectedModule?.id) {
      fetchAll();
    }
  }, [fetchAll, selectedModule?.id]);

  useEffect(() => {
    const fetchAndSetAvailableModules = async () => {
      if (!selectedModule?.id) return;
      
      const modules = await fetchAvailableModules();
      if (modules) {
        const existingIds = new Set([selectedModule.id]);
        let filtered = modules.filter((m: any) => !existingIds.has(m.id));

        if (rightTab === 'dependencies') {
          filtered = filtered.filter((m: any) => 
            !dependencies.some(d => d.id === m.id)
          );
        } else if (rightTab === 'context') {
          filtered = filtered.filter((m: any) => 
            !context.some(c => c.id === m.id)
          );
        }

        setAvailableModules(filtered);
      }
    };

    if (rightTab && selectedModule?.id) {
      fetchAndSetAvailableModules();
    }
  }, [rightTab, dependencies, context, fetchAvailableModules, selectedModule?.id]);

  const handleAddRelation = async (targetModule: RuntimeModule, type: 'dependency' | 'context') => {
    if (!selectedModule?.id) return;
    
    await createRelation(targetModule.id, type);
    const newAvailable = availableModules.filter(m => m.id !== targetModule.id);
    setAvailableModules(newAvailable);
  };

  // Return empty div if no module is selected
  if (!selectedModule?.id) {
    return <div className="h-full flex">
      <div className="flex flex-col gap-2 p-2 border-l bg-background">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" disabled>
                <PackageOpen className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependencies</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" disabled>
                <GitFork className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependents</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" disabled>
                <Network className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Context</TooltipContent>
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

          {rightTab === 'dependencies' && (
            <RelationshipTree
              modules={dependencies}
              title="Dependencies"
              isLoading={isLoading}
              onAddRelation={(module) => handleAddRelation(module, 'dependency')}
              availableModules={availableModules}
            />
          )}
          {rightTab === 'dependents' && (
            <RelationshipTree
              modules={dependents}
              title="Dependents"
              isLoading={isLoading}
            />
          )}
          {rightTab === 'context' && (
            <RelationshipTree
              modules={context}
              title="Context"
              isLoading={isLoading}
              onAddRelation={(module) => handleAddRelation(module, 'context')}
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
                className={rightTab === 'dependencies' ? 'bg-gray-100' : ''}
                onClick={() => setRightTab('dependencies')}
              >
                <PackageOpen className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependencies</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'dependents' ? 'bg-gray-100' : ''}
                onClick={() => setRightTab('dependents')}
              >
                <GitFork className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependents</TooltipContent>
          </Tooltip>
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
        </TooltipProvider>
      </div>
    </div>
  );
};

export default RightSidebar;