import React, { useState, useEffect } from 'react';
import { SidebarClose, Search, Sidebar, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarHeader } from '@/components/ui/sidebar';
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { RegistryKit } from './RegistryPage';

interface RegistryExplorerProps {
  onCollapse: () => void;
}

const RegistryExplorer: React.FC<RegistryExplorerProps> = ({ onCollapse }) => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [kits, setKits] = useState<RegistryKit[]>([]);
  const [filteredKits, setFilteredKits] = useState<RegistryKit[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedKitId, setSelectedKitId] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchKits();
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredKits(kits);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredKits(
        kits.filter(kit => 
          kit.kitConfig.name.toLowerCase().includes(query) || 
          kit.kitConfig.description?.toLowerCase().includes(query) || 
          kit.kitConfig.owner.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, kits]);

  const fetchKits = async () => {
    setIsLoading(true);
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit/registry`);
      if (!response.ok) throw new Error('Failed to fetch registry kits');
      const data = await response.json();
      setKits(data.kits || []);
      setFilteredKits(data.kits || []);
      
      // If there are kits and none is selected, select the first one
      if (data.kits?.length > 0 && !selectedKitId) {
        handleKitClick(data.kits[0]);
      }
    } catch (error) {
      console.error('Error fetching registry kits:', error);
      toast({
        title: "Error",
        description: "Failed to fetch registry kits",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
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

  // Generate a unique ID for each kit
  const getKitUniqueId = (kit: RegistryKit) => {
    return `${kit.kitConfig.owner}/${kit.kitConfig.id}/${kit.kitConfig.version}`;
  };

  const handleKitClick = (kit: RegistryKit) => {
    // Update the selected kit ID for highlighting
    setSelectedKitId(getKitUniqueId(kit));
    
    // Dispatch a custom event to notify MainContentContainer
    const event = new CustomEvent('registry-kit-selected', { 
      detail: JSON.stringify(kit)
    });
    window.dispatchEvent(event);
  };

  return (
    <div className="flex flex-col h-full">
      <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm bg-neutral-900/50 border-b border-gray-800">
        <div className="flex flex-row items-center space-x-4">
          <h2 className="text-lg font-medium text-gray-200">Registry</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onCollapse}
          className="h-8 w-8 rounded-md hover:bg-neutral-800/70 hover:text-gray-100 text-gray-400"
          aria-label="Collapse sidebar"
        >
          <Sidebar size={16} />
        </Button>
      </SidebarHeader>

      <div className="p-3 border-b border-gray-800">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
          <Input
            type="text"
            placeholder="Search modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-neutral-800 border-gray-700 text-gray-100 placeholder:text-gray-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-2">
        <ScrollArea className="h-full">
          <div className="space-y-1">
            {isLoading ? (
              Array(5).fill(0).map((_, index) => (
                <div key={index} className="p-3 rounded-md space-y-2 bg-neutral-800/60">
                  <Skeleton className="h-5 w-3/4 bg-neutral-700" />
                  <Skeleton className="h-4 w-1/2 bg-neutral-700" />
                  <Skeleton className="h-3 w-1/4 bg-neutral-700" />
                </div>
              ))
            ) : filteredKits.length === 0 ? (
              <div className="p-4 text-center text-gray-400">
                No kits match your search criteria
              </div>
            ) : (
              filteredKits.map((kit) => {
                const uniqueId = getKitUniqueId(kit);
                return (
                  <div key={uniqueId} className=" overflow-hidden">
                    <button
                      className={`w-full text-left p-3 m-1 rounded-md transition-colors ${
                        selectedKitId === uniqueId
                          ? "bg-neutral-700 text-white"
                          : "bg-neutral-800/60 hover:bg-neutral-700/80 text-gray-200"
                      }`}
                      onClick={() => handleKitClick(kit)}
                    >
                      <div className="flex items-center w-full overflow-hidden">
                        <div className="flex-1 min-w-0 mr-2">
                          <h3 className="font-medium text-sm truncate">{kit.kitConfig.name}</h3>
                        </div>
                        <Badge variant="outline" className="text-xs bg-neutral-900/70 text-gray-300 border-gray-700 flex-shrink-0">
                          v{kit.kitConfig.version}
                        </Badge>
                      </div>
                      
                      {kit.kitConfig.description && (
                        <p className="text-xs text-gray-400 mt-1 truncate w-full">{kit.kitConfig.description}</p>
                      )}
                      
                      <div className="flex items-center mt-2 text-xs text-gray-500 w-full overflow-hidden">
                        <span className="truncate flex-1 min-w-0">{kit.kitConfig.owner}</span>
                        <span className="mx-1 flex-shrink-0">•</span>
                        <span className="flex-shrink-0">{formatDate(kit.uploadedAt)}</span>
                      </div>
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default RegistryExplorer;