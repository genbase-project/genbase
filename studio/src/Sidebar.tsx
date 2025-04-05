// src/LeftSidebar.tsx
import React from 'react';
import { useLocation } from 'react-router-dom';
// import { handleLogout } from '@/components/Logout'; // Remove this if logout is handled by AuthContext
import ModuleExplorer from './app/module/ModuleExplorer';
import RegistryExplorer from './app/registry/RegistryExplorer';
import SettingsSidebar from '@/app/settings/SettingsSidebar';
import { RegistryKit } from './app/registry/RegistryPage';
import UserManagementExplorer from './app/users/UserManagementExplorer'; // Import the new component
import { useAuth } from './context/AuthContext'; // Import useAuth




import { Link } from 'react-router-dom';
import { Settings, LogOut, Package, Layers, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

export type SidebarTab = {
  id: string;
  path: string;
  name: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
};

interface SidebarNavProps {
  onExpand: (expand: boolean) => void;
}


interface LeftSidebarProps {
  onExpand: (expand: boolean) => void;
  expanded: boolean;
  onRegistryKitSelect: (kit: RegistryKit | null) => void;
}








const SidebarNav: React.FC<SidebarNavProps> = ({
  onExpand,
}) => {
  const location = useLocation();
  const { isSuperuser, logout } = useAuth();
  const currentPath = location.pathname;

  const tabs: SidebarTab[] = [
    { id: "modules", path: "/modules", name: "Modules", icon: <Layers size={24} /> },
    { id: "registry", path: "/registry", name: "Registry", icon: <Package size={24} /> },
    { id: "users", path: "/users", name: "Users & Access", icon: <Users size={24} />, adminOnly: true },
    { id: "settings", path: "/settings", name: "Settings", icon: <Settings size={24} /> },
  ];

  const getActiveTabId = () => {
    if (currentPath.startsWith('/settings')) return 'settings';
    if (currentPath.startsWith('/users')) return 'users';
    const active = tabs.find(tab => tab.id !== 'settings' && tab.id !== 'users' && currentPath.startsWith(tab.path));
    return active ? active.id : null;
  };

  const activeTabId = getActiveTabId();

  return (
    // Nav strip uses muted background, border
    <div className="w-14 h-full flex flex-col bg-neutral-50 border-r border-border">
      <div className="p-2 flex justify-center">
        <Link to="/modules">
            <img src="/logo.png" alt="Genbase Logo" className="h-10 w-10" />
        </Link>
      </div>

      <div className="flex-1 flex flex-col gap-2 p-2 items-center">
        {tabs.map((tab) => {
          if (tab.adminOnly && !isSuperuser) {
            return null;
          }
          return (
            <Button
              key={tab.id}
              variant="ghost"
              size="icon"
              asChild
              onClick={() => { onExpand(true); }}
              className={`h-12 w-12 rounded-md ${
                activeTabId === tab.id
                  // Active: Accent background and text
                  ? "bg-accent text-accent-foreground"
                  // Inactive: Muted text, Accent background/text on hover
                  // NOTE: Background hover might not be visible if accent/muted colors are the same! Text change is key.
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              } transition-colors`}
              aria-label={tab.name}
              title={tab.name}
            >
              <Link to={tab.path}>
                {tab.icon}
              </Link>
            </Button>
          );
        })}
      </div>

      <div className="p-2 space-y-2 mt-auto flex flex-col items-center">
        <Button
          variant="ghost"
          size="icon"
          onClick={logout}
          // Destructive text, subtle destructive background on hover
          className="w-10 h-10 rounded-md text-destructive text-red-500 hover:bg-destructive/10 hover:text-destructive transition-colors"
          aria-label="Logout"
          title="Logout"
        >
          <LogOut size={22} />
        </Button>
      </div>
    </div>
  );
};




const LeftSidebar: React.FC<LeftSidebarProps> = ({
  onExpand,
  expanded,
  onRegistryKitSelect,
}) => {
  const location = useLocation();
  const { isSuperuser } = useAuth(); // Get superuser status

  const getActiveSection = (pathname: string): string => {
    if (pathname.startsWith('/modules')) return 'modules';
    if (pathname.startsWith('/registry')) return 'registry';
    if (pathname.startsWith('/settings')) return 'settings';
    if (pathname.startsWith('/users') && isSuperuser) return 'users'; // Check superuser status
    return 'modules'; // Default or fallback
  };
  const activeSection = getActiveSection(location.pathname);

  const renderSidebarContent = () => {
    if (!expanded) {
      return null;
    }

    // Ensure only superusers see the user management sidebar content
    if (activeSection === 'users' && !isSuperuser) {

        return <div className="p-4 text-muted-foreground">Access Denied</div>; // Changed color
    }


    return (
      <div className="h-full flex-1 overflow-hidden border-r border-border bg-background"> {/* Changed theme variables */}
        {activeSection === "modules" ? (
          <ModuleExplorer onCollapse={() => onExpand(false)} />
        ) : activeSection === "registry" ? (
          <RegistryExplorer
             onCollapse={() => onExpand(false)}
             onKitSelect={onRegistryKitSelect}
          />
        ) : activeSection === "settings" ? (
          <SettingsSidebar onCollapse={() => onExpand(false)} />
        ) : activeSection === "users" ? ( // Render User Management Sidebar
           <UserManagementExplorer onCollapse={() => onExpand(false)} />
        ) : (
          <div className="p-4 text-muted-foreground">Select a section</div> // Changed color, Fallback
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-row bg-background w-full overflow-hidden"> {/* Changed theme variable */}
      <SidebarNav
        onExpand={onExpand}
      />
      {renderSidebarContent()}
    </div>
  );
};

export default LeftSidebar;





































