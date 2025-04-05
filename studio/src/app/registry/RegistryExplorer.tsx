import React, { useState, useEffect } from 'react';
import { Search, Sidebar, Package } from "lucide-react";
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
  onKitSelect: (kit: RegistryKit | null) => void;
}

const RegistryExplorer: React.FC<RegistryExplorerProps> = ({
    onCollapse,
    onKitSelect
}) => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [kits, setKits] = useState<RegistryKit[]>([]);
  const [filteredKits, setFilteredKits] = useState<RegistryKit[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedKitId, setSelectedKitId] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchKits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredKits(kits);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredKits(
        kits.filter(kit =>
          kit.kitConfig.name.toLowerCase().includes(query) ||
          (kit.kitConfig.description && kit.kitConfig.description.toLowerCase().includes(query)) ||
          kit.kitConfig.owner.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, kits]);

  const fetchKits = async () => {
    setIsLoading(true);
    setSelectedKitId(undefined);
    onKitSelect(null);
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit/registry`);
      if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Failed to fetch registry kits' }));
           throw new Error(errorData.detail || errorData.message || 'Failed to fetch registry kits');
      }
      const data = await response.json();
      const fetchedKits = data.kits || [];
      setKits(fetchedKits);
      setFilteredKits(fetchedKits);
    } catch (error: any) {
      console.error('Error fetching registry kits:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to fetch registry kits",
        variant: "destructive"
      });
      setKits([]);
      setFilteredKits([]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        return date.toLocaleDateString('en-US', {
          year: 'numeric', month: 'short', day: 'numeric'
        });
    } catch (e) {
        console.error("Error formatting date:", dateString, e);
        return 'Invalid Date';
    }
  };

  const getKitUniqueId = (kit: RegistryKit) => {
    const owner = kit.kitConfig?.owner ?? 'unknown';
    const id = kit.kitConfig?.id ?? kit.kitConfig?.name ?? 'unknown_kit';
    const version = kit.kitConfig?.version ?? 'latest';
    return `${owner}/${id}/${version}`;
  };

  const handleKitClick = (kit: RegistryKit) => {
    const uniqueId = getKitUniqueId(kit);
    console.log(`RegistryExplorer: Kit clicked - ID: ${uniqueId}, Name: ${kit.kitConfig.name}`);
    setSelectedKitId(uniqueId);
    onKitSelect(kit);
  };

  return (
    // Use muted background for the sidebar, standard text color
    <div className="flex flex-col h-full bg-neutral-50 text-foreground">
      {/* Header uses muted background, border, standard text color */}
      <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm bg-neutral-50/90 border-b border-border flex-shrink-0">
        <div className="flex flex-row items-center space-x-2">
           <Package size={20} className="text-muted-foreground"/> {/* Icon color */}
          <h2 className="text-lg font-medium text-foreground">Registry</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onCollapse}
          // Muted text, slightly darker neutral background on hover
          className="h-8 w-8 rounded-md text-muted-foreground hover:bg-neutral-200 hover:text-foreground"
          aria-label="Collapse sidebar"
        >
          <Sidebar size={16} />
        </Button>
      </SidebarHeader>

      {/* Search area uses muted background, border */}
      <div className="p-3 border-b border-border flex-shrink-0">
        <div className="relative">
           {/* Muted text color for search icon */}
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search kits..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            // Standard input styling for light theme
            className="pl-9 bg-background border-border text-foreground placeholder:text-muted-foreground h-9 focus:ring-primary"
          />
        </div>
      </div>

      {/* Scrollable area for kits */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full p-2">
          <div className="space-y-1">
            {isLoading ? (
              Array(5).fill(0).map((_, index) => (
                // Skeleton with lighter neutral background
                <div key={index} className="p-3 rounded-md space-y-2 bg-neutral-100 animate-pulse">
                  <Skeleton className="h-5 w-3/4 bg-neutral-200 rounded" />
                  <Skeleton className="h-4 w-1/2 bg-neutral-200 rounded" />
                  <div className="flex justify-between">
                    <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                    <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                  </div>
                </div>
              ))
            ) : filteredKits.length === 0 ? (
               // Muted text color for empty state
              <div className="p-4 text-center text-muted-foreground text-sm">
                {searchQuery ? "No kits match your search." : "No kits found in the registry."}
              </div>
            ) : (
              filteredKits.map((kit) => {
                if (!kit.kitConfig) {
                  console.warn("RegistryExplorer: Skipping kit with missing kitConfig", kit);
                  return null;
                }
                const uniqueId = getKitUniqueId(kit);
                return (
                  <button
                    key={uniqueId}
                    className={`w-full text-left p-3 rounded-md transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-opacity-50 ${
                      selectedKitId === uniqueId
                        // Selected state: Darker neutral background
                        ? "bg-neutral-200 text-foreground shadow-sm"
                         // Normal state: Light neutral background, hover to slightly darker neutral
                        : "bg-neutral-100 hover:bg-neutral-200 text-foreground"
                    }`}
                    onClick={() => handleKitClick(kit)}
                    aria-pressed={selectedKitId === uniqueId}
                  >
                    <div className="flex items-center justify-between w-full overflow-hidden mb-1">
                      {/* Use standard foreground text */}
                      <h3 className="font-medium text-sm truncate text-foreground">{kit.kitConfig.name}</h3>
                       {/* Badge with neutral colors */}
                      <Badge variant="secondary" className="text-xs bg-neutral-200 text-neutral-700 border-neutral-300 flex-shrink-0 px-1.5 py-0.5">
                        v{kit.kitConfig.version}
                      </Badge>
                    </div>

                    {kit.kitConfig.description && (
                      // Muted foreground for description
                      <p className="text-xs text-muted-foreground mt-1 mb-2 truncate w-full">{kit.kitConfig.description}</p>
                    )}

                    <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground w-full overflow-hidden">
                       {/* Muted foreground for owner/date */}
                      <span className="truncate flex-1 min-w-0 mr-2">{kit.kitConfig.owner}</span>
                      <span className="flex-shrink-0">{formatDate(kit.uploadedAt)}</span>
                    </div>
                  </button>
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