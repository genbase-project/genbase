import { useState, useCallback } from 'react';
import { Module } from '../components/TreeView';
import { toast } from '@/hooks/use-toast';
import { DEFAULT_PROJECT_ID } from '../lib/tree';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';

export const useModuleRelationships = (moduleId: string) => {
  const [context, setContext] = useState<Module[]>([]);
  const [connections, setConnections] = useState<Module[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchContext = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/context`);
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

  const fetchConnections = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/${moduleId}/connections`);
      const data = await response.json();
      setConnections(data);
    } catch (error) {
      console.error('Error fetching connections:', error);
      toast({
        title: "Error",
        description: "Failed to fetch connections",
        variant: "destructive"
      });
    }
  }, [moduleId]);

  const fetchAvailableModules = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/project/${DEFAULT_PROJECT_ID}/list`);
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

  const createConnection = useCallback(async (targetId: string, relationType: 'context' | 'connection') => {
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/module/relation`, {
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

      toast({
        title: "Success",
        description: "Relationship created successfully"
      });

      // Refresh the relevant list
      if (relationType === 'context') {
        await fetchContext();
      } else {
        await fetchConnections();
      }
    } catch (error) {
      console.error('Error creating connection:', error);
      toast({
        title: "Error",
        description: "Failed to create relationship",
        variant: "destructive"
      });
    }
  }, [moduleId, fetchContext, fetchConnections]);

  const removeConnection = useCallback(async (targetId: string, relationType: 'context' | 'connection') => {
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/module/relation/${moduleId}/${targetId}/${relationType}`, 
        { method: 'DELETE' }
      );

      toast({
        title: "Success",
        description: "Relationship removed successfully"
      });

      // Refresh both lists since the relationship might have changed
      await Promise.all([fetchContext(), fetchConnections()]);
    } catch (error) {
      console.error('Error removing connection:', error);
      toast({
        title: "Error",
        description: "Failed to remove relationship",
        variant: "destructive"
      });
    }
  }, [moduleId, fetchContext, fetchConnections]);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchContext(),
        fetchConnections()
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [fetchContext, fetchConnections]);

  return {
    context,
    connections,
    isLoading,
    fetchAll,
    createConnection,
    removeConnection,
    fetchAvailableModules
  };
};
