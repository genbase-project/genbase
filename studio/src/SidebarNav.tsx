import React from 'react';
import { Sidebar, Settings, LogOut, Package, Layers, Grid } from "lucide-react";
import { Button } from "@/components/ui/button";

// Define the tabs for the sidebar
export type SidebarTab = {
  id: string;
  name: string;
  icon: React.ReactNode;
};

interface SidebarNavProps {
  onTabChange: (tabId: string) => void;
  activeTab: string;
  onExpand: (expand: boolean) => void;
  onSettingsOpen: () => void;
  onLogout: () => void;
}

const SidebarNav: React.FC<SidebarNavProps> = ({ 
  onTabChange, 
  activeTab, 
  onExpand, 
  onSettingsOpen, 
  onLogout 
}) => {
  // Define the tabs
  const tabs: SidebarTab[] = [
    { id: "modules", name: "Modules", icon: <Layers size={24} /> },
    { id: "registry", name: "Registry", icon: <Package size={24} /> },
    // { id: "other", name: "Other", icon: <Grid size={24} /> }
  ];

  return (
    <div className="w-14 h-full flex flex-col bg-neutral-950 border-r border-gray-800">
      <div className="p-2 flex justify-center">
        <img src="/logo.png" alt="Genbase Logo" className="h-10 w-10" />
      </div>
      
      <div className="flex-1 flex flex-col gap-2 p-2 items-center">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant="ghost"
            size="icon"
            onClick={() => {
              onTabChange(tab.id);
              onExpand(true); // Auto-expand when clicking a tab
            }}
            className={`h-12 w-12 rounded-md ${
              activeTab === tab.id 
                ? "bg-neutral-800 text-white" 
                : "hover:bg-neutral-800/70 text-gray-500 hover:text-gray-300"
            } transition-colors`}
            aria-label={tab.name}
            title={tab.name}
          >
            {tab.icon}
          </Button>
        ))}
      </div>
      
      <div className="p-2 space-y-2 mt-auto">
        <Button
          variant="ghost"
          size="icon"
          onClick={onSettingsOpen}
          className="w-10 h-10 rounded-md hover:bg-neutral-800/70 hover:text-gray-100 text-gray-500 transition-colors"
          aria-label="Settings"
          title="Settings"
        >
          <Settings size={22} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onLogout}
          className="w-10 h-10 rounded-md hover:bg-neutral-800/70 text-red-500 hover:text-red-400 transition-colors"
          aria-label="Logout"
          title="Logout"
        >
          <LogOut size={22} />
        </Button>
      </div>
    </div>
  );
};

export default SidebarNav;