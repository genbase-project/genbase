import React from 'react';
import { SidebarClose, Search, Sidebar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarHeader } from '@/components/ui/sidebar';

interface RegistryExplorerProps {
  onCollapse: () => void;
}

const RegistryExplorer: React.FC<RegistryExplorerProps> = ({ onCollapse }) => {
  return (
    <div className="flex flex-col h-full">
      <SidebarHeader className="px-3 py-4 flex-row justify-between items-center backdrop-blur-sm bg-neutral-900/50 border-b border-gray-800">
        <h2 className="text-lg font-medium text-gray-200">Registry</h2>
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

      <div className="p-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
          <Input
            type="text"
            placeholder="Search module kits..."
            className="pl-9 bg-neutral-800 border-gray-700 text-gray-100 placeholder:text-gray-500"
          />
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col items-center justify-center">
        <div className="text-center space-y-4 max-w-xs">
          <h3 className="text-xl font-semibold text-gray-200">Registry Explorer</h3>
          <p className="text-gray-400 text-sm">
            The registry will provide a centralized repository where you can discover, share, and manage modules.
          </p>
          <p className="text-gray-400 text-sm">
            This feature is currently under development.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegistryExplorer;