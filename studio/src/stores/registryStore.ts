// src/stores/registryStore.ts
import { create } from 'zustand';
import { RegistryKit } from '@/app/registry/RegistryPage';

// Interface for installed kits (from /kit endpoint)
export interface InstalledKit {
  name: string;
  version: string;
  created_at: string;
  size: number;
  owner: string;
  doc_version: string;
  kit_id: string;
  environment: Array<{
    name: string;
    description: string;
    required: boolean;
    default?: string;
  }>;
}

interface RegistryState {
  // All kits from the registry API
  allKits: RegistryKit[];
  // Grouped kits (for display in explorer)
  groupedKits: Record<string, RegistryKit[]>;
  // Installed kits from the /kit endpoint
  installedKits: InstalledKit[];
  // Currently selected kit ID (owner/id format)
  selectedKitId: string | null;
  // Currently selected kit version
  selectedVersion: string | null;
  // Available versions for selected kit
  availableVersions: string[];
  // Loading states
  isLoading: boolean;
  isInstalledLoading: boolean;

  setAllKits: (kits: RegistryKit[]) => void;
  setInstalledKits: (kits: InstalledKit[]) => void;
  setLoading: (loading: boolean) => void;
  setInstalledLoading: (loading: boolean) => void;
  selectKit: (kitId: string, version?: string) => void;
  selectVersion: (version: string) => void;
  getSelectedKit: () => RegistryKit | null;
  isKitInstalled: (owner: string, kitId: string, version?: string) => boolean;
}

// Helper to get kit identifier without version
const getKitBaseId = (kit: RegistryKit | { owner: string, kit_id: string }) => {
  if ('kitConfig' in kit) {
    const owner = kit.kitConfig?.owner ?? 'unknown';
    const id = kit.kitConfig?.id ?? kit.kitConfig?.name ?? 'unknown_kit';
    return `${owner}/${id}`;
  } else {
    return `${kit.owner}/${kit.kit_id}`;
  }
};

// Helper to get kit with full version identifier 
const getKitFullId = (kit: RegistryKit) => {
  const baseId = getKitBaseId(kit);
  const version = kit.kitConfig?.version ?? 'latest';
  return `${baseId}/${version}`;
};

// Group kits by base ID
const groupKitsByBaseId = (kits: RegistryKit[]): Record<string, RegistryKit[]> => {
  const grouped: Record<string, RegistryKit[]> = {};
  
  kits.forEach(kit => {
    const baseId = getKitBaseId(kit);
    if (!grouped[baseId]) {
      grouped[baseId] = [];
    }
    grouped[baseId].push(kit);
  });

  // Sort versions within each group (newest first)
  Object.keys(grouped).forEach(baseId => {
    grouped[baseId].sort((a, b) => {
      // Try to compare versions as semver (descending)
      return b.kitConfig.version.localeCompare(a.kitConfig.version, undefined, { numeric: true });
    });
  });
  
  return grouped;
};

export const useRegistryStore = create<RegistryState>((set, get) => ({
  allKits: [],
  groupedKits: {},
  installedKits: [],
  selectedKitId: null,
  selectedVersion: null,
  availableVersions: [],
  isLoading: false,
  isInstalledLoading: false,

  setAllKits: (kits) => {
    const groupedKits = groupKitsByBaseId(kits);
    set({ 
      allKits: kits,
      groupedKits
    });
  },

  setInstalledKits: (kits) => {
    set({ installedKits: kits });
  },

  setLoading: (loading) => set({ isLoading: loading }),
  
  setInstalledLoading: (loading) => set({ isInstalledLoading: loading }),

  selectKit: (kitId, version) => {
    const { groupedKits } = get();
    
    if (groupedKits[kitId]) {
      // Get all versions for this kit
      const versions = groupedKits[kitId].map(kit => kit.kitConfig.version);
      
      // If version is specified and exists, use it, otherwise use latest
      const selectVersion = version && versions.includes(version) 
        ? version 
        : groupedKits[kitId][0].kitConfig.version;
      
      set({ 
        selectedKitId: kitId,
        selectedVersion: selectVersion,
        availableVersions: versions
      });
    }
  },

  selectVersion: (version) => {
    set({ selectedVersion: version });
  },

  getSelectedKit: () => {
    const { selectedKitId, selectedVersion, groupedKits } = get();
    
    if (!selectedKitId || !selectedVersion) return null;
    
    const kitVersions = groupedKits[selectedKitId];
    if (!kitVersions) return null;
    
    return kitVersions.find(kit => kit.kitConfig.version === selectedVersion) || null;
  },
  
  isKitInstalled: (owner, kitId, version) => {
    const { installedKits } = get();
    
    return installedKits.some(kit => 
      kit.owner === owner && 
      kit.kit_id === kitId && 
      (version ? kit.version === version : true)
    );
  }
}));