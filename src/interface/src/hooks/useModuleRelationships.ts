import { useState, useCallback } from 'react';
import { RuntimeModule } from '../components/TreeView';
import { buildTreeFromModules } from '../lib/tree';
import { toast } from '@/hooks/use-toast';
import { DEFAULT_PROJECT_ID } from '../lib/tree';

const API_BASE = 'http://localhost:8000';

export const useModuleRelationships = (moduleId: string) => {
  const [dependencies, setDependencies] = useState<RuntimeModule[]>([]);
  const [dependents, setDependents] = useState<RuntimeModule[]>([]);
  const [context, setContext] = useState<RuntimeModule[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchDependencies = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/runtime/module/${moduleId}/dependencies`);
      if (!response.ok) throw new Error('Failed to fetch dependencies');
      const data = await response.json();
      setDependencies(data);
    } catch (error) {
      console.error('Error fetching dependencies:', error);
      toast({
        title: "Error",
        description: "Failed to fetch dependencies",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchDependents = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/runtime/module/${moduleId}/dependents`);
      if (!response.ok) throw new Error('Failed to fetch dependents');
      const data = await response.json();
      setDependents(data);
    } catch (error) {
      console.error('Error fetching dependents:', error);
      toast({
        title: "Error",
        description: "Failed to fetch dependents",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchContext = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/runtime/module/${moduleId}/context`);
      if (!response.ok) throw new Error('Failed to fetch context');
      const data = await response.json();
      setContext(data);
    } catch (error) {
      console.error('Error fetching context:', error);
      toast({
        title: "Error",
        description: "Failed to fetch context relations",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchAvailableModules = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/runtime/project/${DEFAULT_PROJECT_ID}/modules`);
      if (!response.ok) throw new Error('Failed to fetch available modules');
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching available modules:', error);
      toast({
        title: "Error",
        description: "Failed to fetch available modules",
        variant: "destructive"
      });
      return null;
    }
  }, []);

  const createRelation = useCallback(async (targetId: string, relationType: 'dependency' | 'context') => {
    try {
      const response = await fetch(`${API_BASE}/runtime/relation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_id: moduleId,
          target_id: targetId,
          relation_type: relationType
        }),
      });

      if (!response.ok) throw new Error('Failed to create relation');

      toast({
        title: "Success",
        description: "Relation created successfully"
      });

      // Refresh the relevant list
      if (relationType === 'dependency') {
        await fetchDependencies();
      } else {
        await fetchContext();
      }
    } catch (error) {
      console.error('Error creating relation:', error);
      toast({
        title: "Error",
        description: "Failed to create relation",
        variant: "destructive"
      });
    }
  }, [moduleId, fetchDependencies, fetchContext]);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchDependencies(),
        fetchDependents(),
        fetchContext()
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [fetchDependencies, fetchDependents, fetchContext]);

  return {
    dependencies,
    dependents,
    context,
    isLoading,
    fetchAll,
    createRelation,
    fetchAvailableModules
  };
};