import React, { useState, useEffect } from 'react';
import { Search, Sidebar, Package, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarHeader } from '@/components/ui/sidebar';
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { RegistryKit } from './RegistryPage';
import { useRegistryStore, InstalledKit } from '@/stores/registryStore';

interface RegistryExplorerProps {
  onCollapse: () => void;
  onKitSelect: (kit: RegistryKit | null) => void;
}

const RegistryExplorer: React.FC<RegistryExplorerProps> = ({
    onCollapse,
    onKitSelect
}) => {
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredGroupedKits, setFilteredGroupedKits] = useState<Record<string, RegistryKit[]>>({});
  const [activeTab, setActiveTab] = useState<'registry' | 'installed'>('registry');
  const [filteredInstalledKits, setFilteredInstalledKits] = useState<InstalledKit[]>([]);
  
  // Get registry state from store
  const { 
    isLoading, 
    isInstalledLoading,
    groupedKits, 
    selectedKitId,
    installedKits,
    isKitInstalled,
    setAllKits, 
    setInstalledKits,
    setLoading,
    setInstalledLoading, 
    selectKit,
    getSelectedKit
  } = useRegistryStore();

  // Fetch kits on mount
  useEffect(() => {
    fetchKits();
    fetchInstalledKits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Filter kits based on search query and active tab
  useEffect(() => {
    if (activeTab === 'registry') {
      if (searchQuery.trim() === '') {
        setFilteredGroupedKits(groupedKits);
      } else {
        const query = searchQuery.toLowerCase();
        const filtered: Record<string, RegistryKit[]> = {};
        
        Object.entries(groupedKits).forEach(([kitId, kitVersions]) => {
          // Check if at least one version matches search criteria
          const matchingVersions = kitVersions.filter(kit => 
            kit.kitConfig.name.toLowerCase().includes(query) ||
            (kit.kitConfig.description && kit.kitConfig.description.toLowerCase().includes(query)) ||
            kit.kitConfig.owner.toLowerCase().includes(query)
          );
          
          if (matchingVersions.length > 0) {
            filtered[kitId] = matchingVersions;
          }
        });
        
        setFilteredGroupedKits(filtered);
      }
    } else {
      // Filter installed kits
      if (searchQuery.trim() === '') {
        setFilteredInstalledKits(installedKits);
      } else {
        const query = searchQuery.toLowerCase();
        const filtered = installedKits.filter(kit => 
          kit.name.toLowerCase().includes(query) ||
          kit.owner.toLowerCase().includes(query) ||
          kit.kit_id.toLowerCase().includes(query)
        );
        setFilteredInstalledKits(filtered);
      }
    }
  }, [searchQuery, groupedKits, activeTab, installedKits]);

  const fetchKits = async () => {
    setLoading(true);
    selectKit(null as any);
    onKitSelect(null);
    
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit/registry`);
      if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Failed to fetch registry kits' }));
           throw new Error(errorData.detail || errorData.message || 'Failed to fetch registry kits');
      }
      const data = await response.json();
      const fetchedKits = data.kits || [];
      setAllKits(fetchedKits);
    } catch (error: any) {
      console.error('Error fetching registry kits:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to fetch registry kits",
        variant: "destructive"
      });
      setAllKits([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchInstalledKits = async () => {
    setInstalledLoading(true);
    try {
      const response = await fetchWithAuth(`${ENGINE_BASE_URL}/kit`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to fetch installed kits' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to fetch installed kits');
      }
      const installedKitsData = await response.json();
      setInstalledKits(installedKitsData.kits);
      setFilteredInstalledKits(installedKitsData.kits);
    } catch (error: any) {
      console.error('Error fetching installed kits:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to fetch installed kits",
        variant: "destructive"
      });
      setInstalledKits([]);
    } finally {
      setInstalledLoading(false);
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

  const getKitBaseId = (kit: RegistryKit) => {
    const owner = kit.kitConfig?.owner ?? 'unknown';
    const id = kit.kitConfig?.id ?? kit.kitConfig?.name ?? 'unknown_kit';
    return `${owner}/${id}`;
  };

  const handleKitClick = (kitBaseId: string) => {
    console.log(`RegistryExplorer: Kit group clicked - ID: ${kitBaseId}`);
    selectKit(kitBaseId);
    // Get the latest version of the kit to pass to the registry page
    const selectedKit = getSelectedKit();
    if (selectedKit) {
      onKitSelect(selectedKit);
    }
  };

  // Handle click on installed kit (we'll need to find it in registry kits)
  const handleInstalledKitClick = (kit: InstalledKit) => {
    const kitBaseId = `${kit.owner}/${kit.kit_id}`;
    // Try to find this kit in registry to display its details
    if (groupedKits[kitBaseId]) {
      selectKit(kitBaseId, kit.version);
      const selectedKit = getSelectedKit();
      if (selectedKit) {
        onKitSelect(selectedKit);
      }
    } else {
      // If not found in registry, we need to handle this case
      // For now, just show a toast message
      toast({
        title: "Kit Info Unavailable",
        description: `Details for ${kit.name} (v${kit.version}) are not available in the registry.`,
        variant: "default"
      });
    }
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value as 'registry' | 'installed');
    setSearchQuery('');
  };

  return (
    // Use muted background for the sidebar, standard text color
    <div className="flex flex-col h-full bg-neutral-50 text-foreground">
      {/* Header uses muted background, border, standard text color */}
      <SidebarHeader className="px-3 py-4 flex flex-row justify-between items-center backdrop-blur-sm bg-neutral-50/90 border-b border-border flex-shrink-0">
        <div className="flex flex-row items-center space-x-2">
           <Package size={20} className="text-muted-foreground"/>
          <h2 className="text-lg font-medium text-foreground">Registry</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onCollapse}
          className="h-8 w-8 rounded-md text-muted-foreground hover:bg-neutral-200 hover:text-foreground"
          aria-label="Collapse sidebar"
        >
          <Sidebar size={16} />
        </Button>
      </SidebarHeader>

      {/* Tabs for switching between registry and installed kits */}
      <div className="border-b border-border">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid grid-cols-2 bg-neutral-50">
            <TabsTrigger value="registry" className="text-sm">Registry Kits</TabsTrigger>
            <TabsTrigger value="installed" className="text-sm">Installed Kits</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Search area uses muted background, border */}
      <div className="p-3 border-b border-border flex-shrink-0">
        <div className="relative">
           {/* Muted text color for search icon */}
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder={`Search ${activeTab === 'registry' ? 'registry' : 'installed'} kits...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-background border-border text-foreground placeholder:text-muted-foreground h-9 focus:ring-primary"
          />
        </div>
      </div>

      {/* Scrollable area for kits */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full p-2">
          <div className="space-y-1">
            {/* REGISTRY KITS */}
            {activeTab === 'registry' && (
              isLoading ? (
                Array(5).fill(0).map((_, index) => (
                  <div key={index} className="p-3 rounded-md space-y-2 bg-neutral-100 animate-pulse">
                    <Skeleton className="h-5 w-3/4 bg-neutral-200 rounded" />
                    <Skeleton className="h-4 w-1/2 bg-neutral-200 rounded" />
                    <div className="flex justify-between">
                      <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                      <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                    </div>
                  </div>
                ))
              ) : Object.keys(filteredGroupedKits).length === 0 ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  {searchQuery ? "No kits match your search." : "No kits found in the registry."}
                </div>
              ) : (
                Object.entries(filteredGroupedKits).map(([kitId, kitVersions]) => {
                  // Use the latest version (first in the array) for display
                  const kit = kitVersions[0];
                  if (!kit.kitConfig) {
                    console.warn("RegistryExplorer: Skipping kit with missing kitConfig", kit);
                    return null;
                  }
                  
                  // Check if any version of this kit is installed
                  const installed = isKitInstalled(kit.kitConfig.owner, kit.kitConfig.id);
                  
                  return (
                    <button
                      key={kitId}
                      className={`w-full text-left p-3 rounded-md transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-opacity-50 ${
                        selectedKitId === kitId
                          ? "bg-neutral-200 text-foreground shadow-sm"
                          : "bg-neutral-100 hover:bg-neutral-200 text-foreground"
                      }`}
                      onClick={() => handleKitClick(kitId)}
                      aria-pressed={selectedKitId === kitId}
                    >
                      <div className="flex items-center justify-between w-full overflow-hidden mb-1">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium text-sm truncate text-foreground">{kit.kitConfig.name}</h3>
                          {installed && (
                            <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
                          )}
                        </div>
                        <Badge variant="secondary" className="text-xs bg-neutral-200 text-neutral-700 border-neutral-300 flex-shrink-0 px-1.5 py-0.5">
                          {kitVersions.length > 1 ? `${kitVersions.length} versions` : `1 version`}
                        </Badge>
                      </div>

                      {kit.kitConfig.description && (
                        <p className="text-xs text-muted-foreground mt-1 mb-2 truncate w-full">{kit.kitConfig.description}</p>
                      )}

                      <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground w-full overflow-hidden">
                        <span className="truncate flex-1 min-w-0 mr-2">{kit.kitConfig.owner}</span>
                        <span className="flex-shrink-0">{formatDate(kit.uploadedAt)}</span>
                      </div>
                    </button>
                  );
                })
              )
            )}

            {/* INSTALLED KITS */}
            {activeTab === 'installed' && (
              isInstalledLoading ? (
                Array(3).fill(0).map((_, index) => (
                  <div key={index} className="p-3 rounded-md space-y-2 bg-neutral-100 animate-pulse">
                    <Skeleton className="h-5 w-3/4 bg-neutral-200 rounded" />
                    <div className="flex justify-between">
                      <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                      <Skeleton className="h-3 w-1/4 bg-neutral-200 rounded" />
                    </div>
                  </div>
                ))
              ) : filteredInstalledKits.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  {searchQuery ? "No installed kits match your search." : "No kits are currently installed."}
                </div>
              ) : (
                filteredInstalledKits.map((kit) => {
                  const kitBaseId = `${kit.owner}/${kit.kit_id}`;
                  
                  return (
                    <button
                      key={`${kitBaseId}-${kit.version}`}
                      className={`w-full text-left p-3 rounded-md transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-opacity-50 ${
                        selectedKitId === kitBaseId
                          ? "bg-neutral-200 text-foreground shadow-sm"
                          : "bg-neutral-100 hover:bg-neutral-200 text-foreground"
                      }`}
                      onClick={() => handleInstalledKitClick(kit)}
                      aria-pressed={selectedKitId === kitBaseId}
                    >
                      <div className="flex items-center justify-between w-full overflow-hidden mb-1">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium text-sm truncate text-foreground">{kit.name}</h3>
                          <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
                        </div>
                        <Badge variant="secondary" className="text-xs bg-neutral-200 text-neutral-700 border-neutral-300 flex-shrink-0 px-1.5 py-0.5">
                          v{kit.version}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground w-full overflow-hidden">
                        <span className="truncate flex-1 min-w-0 mr-2">{kit.owner}</span>
                        <span className="flex-shrink-0">{formatDate(kit.created_at)}</span>
                      </div>
                    </button>
                  );
                })
              )
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default RegistryExplorer;