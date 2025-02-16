import { Network } from 'lucide-react';
import { Module } from '../components/TreeView';
import { useEffect, useState } from "react";
import { useModuleRelationships } from "@/hooks/useModuleRelationships";
import { ModuleWithRelations, RelationshipTree, RelationshipType } from "@/components/RelationshipTree";


const RightSidebar: React.FC<{
  selectedModule?: Module | null;
}> = ({ selectedModule }) => {
  const [availableModules, setAvailableModules] = useState<Module[]>([]);
  
  const {
    context,
    connections,
    isLoading,
    fetchAll,
    createConnection,
    removeConnection,
    fetchAvailableModules
  } = useModuleRelationships(selectedModule?.module_id || '');

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
        const existingIds = new Set([
          selectedModule.module_id,
          ...context.map(m => m.module_id),
          ...connections.map(m => m.module_id)
        ]);
        
        const filtered = modules.filter((m: { id: string; }) => !existingIds.has(m.id));
        setAvailableModules(filtered);
      }
    };

    if (selectedModule?.module_id) {
      fetchAndSetAvailableModules();
    }
  }, [context, connections, fetchAvailableModules, selectedModule?.module_id]);

  const handleAddConnection = async (targetModule: Module, types: RelationshipType[]) => {
    if (!selectedModule?.module_id) return;
    
    for (const type of types) {
      await createConnection(targetModule.module_id, type);
    }
    
    const newAvailable = availableModules.filter(m => m.module_id !== targetModule.module_id);
    setAvailableModules(newAvailable);
  };

  const handleRemoveConnection = async (targetId: string, type: RelationshipType) => {
    if (!selectedModule?.module_id) return;
    await removeConnection(targetId, type);
  };

  const modulesWithRelations = Object.values(
    [...context, ...connections].reduce((acc, curr) => {
      if (!acc[curr.module_id]) {
        acc[curr.module_id] = {
          ...curr,
          relationTypes: []
        };
      }
      
      const isContext = context.some(m => m.module_id === curr.module_id);
      const isConnection = connections.some(m => m.module_id === curr.module_id);
      
      acc[curr.module_id].relationTypes = [
        ...(isContext ? ['context' as const] : []),
        ...(isConnection ? ['connection' as const] : [])
      ];
      
      return acc;
    }, {} as Record<string, ModuleWithRelations>)
  );

  if (!selectedModule?.module_id) {
    return (
      <div className="h-full flex">
        <div className="flex flex-col text-center justify-center gap-2 p-2 border-l bg-background">
        <div className="text-center justify-center">
            <Network className="w-12 h-12 text-gray-400 mb-2 mx-auto" strokeWidth={1.5} />
            
            <h2 className="text-xl font-semibold text-gray-700 mb-2">No Module Selected</h2>
            <p className="text-gray-500">Select a module from the sidebar to explore its contents</p>
          
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex border-l">
      <div className="flex-1">
        <RelationshipTree
          modules={modulesWithRelations}
          isLoading={isLoading}
          onAddRelation={handleAddConnection}
          onRemoveRelation={handleRemoveConnection}
          availableModules={availableModules}
          currentModuleId={selectedModule.module_id}
        />
      </div>
    </div>
  );
};

export default RightSidebar;