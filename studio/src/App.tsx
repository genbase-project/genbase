// src/App.tsx
import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom'; // Import useLocation
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import 'react-complex-tree/lib/style-modern.css';
import LeftSidebar from './Sidebar';
import MainContent from './app/module/layout/MainContent';
import BottomPanel from './app/module/layout/BottomPanel';
import RegistryPage, { RegistryKit } from './app/registry/RegistryPage';
import ModelSettings from './app/settings/ModelSettings';
import { ThemeProvider } from './components/themeProvider';
import { useModuleStore } from './stores/store';
import { GripHorizontal } from 'lucide-react';
import { Toaster } from './components/ui/toaster';
import UserManagementPage from './app/users/UserManagementPage'; // Import the new page
import { useAuth } from './context/AuthContext'; // Import useAuth
import PasswordResetPage from './app/settings/PasswordResetPage';
import { useRegistryStore } from './stores/registryStore';

// --- ModuleLayout and SettingsLayout remain the same ---
const ModuleLayout = () => {
  const selectedModule = useModuleStore(state => state.selectedModule);
  const [isBottomPanelMaximized, setIsBottomPanelMaximized] = useState(false);
  const topPanelSize = isBottomPanelMaximized ? 10 : 65;
  const bottomPanelSize = isBottomPanelMaximized ? 90 : 35;

  const toggleMaximized = (maximize: boolean | ((prevState: boolean) => boolean)) => {
    const shouldMaximize = typeof maximize === 'function' ? maximize(isBottomPanelMaximized) : maximize;
    setIsBottomPanelMaximized(shouldMaximize);
  };

  return (
     <ResizablePanelGroup direction="vertical" className="h-full">
            <ResizablePanel defaultSize={topPanelSize} minSize={10} maxSize={90} className="h-full">
              <div className="h-full overflow-hidden">
                <MainContent selectedModule={selectedModule} />
              </div>
            </ResizablePanel>
            <ResizableHandle withHandle className="bg-border data-[resize-handle-state=drag]:bg-indigo-500">
              <div className="flex h-full w-full items-center justify-center">
                <GripHorizontal className="h-3 w-3 text-muted-foreground" /> {/* Adjusted color */}
              </div>
            </ResizableHandle>
            <ResizablePanel defaultSize={bottomPanelSize} minSize={10} maxSize={90} className="h-full">
              <div className="h-full overflow-hidden">
                <BottomPanel
                  selectedModule={selectedModule}
                  onMaximize={toggleMaximized}
                  isMaximized={isBottomPanelMaximized}
                />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
  );
}

const SettingsLayout = () => {
    return (
        <div className="h-full w-full bg-background text-foreground"> {/* Changed to theme variables */}
            <Outlet />
        </div>
    );
};
// --- End of unchanged layouts ---


// Component to protect routes based on superuser status
const SuperuserRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { isSuperuser, isLoading, isAuthenticated } = useAuth();
    const location = useLocation();

    if (isLoading) {
        // Optional: Show a loading spinner
        return <div className="h-full flex items-center justify-center bg-background"><p className="text-foreground">Loading...</p></div>; // Changed to theme variables
    }

    if (!isAuthenticated) {
         return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!isSuperuser) {
        // Optional: Show an access denied message or redirect to a safe page
        return <Navigate to="/modules" replace />; // Redirect non-superusers
    }

    return <>{children}</>;
};


const App = () => {
  // Initialize with expanded state from localStorage, defaulting to true if not found
  const getInitialSidebarState = () => {
    const savedState = localStorage.getItem('sidebarExpanded');
    // Default to true if nothing saved
    return savedState === null ? true : savedState === 'true';
  };
  
  const [sidebarExpand, setSidebarExpand] = useState(getInitialSidebarState);
  const [selectedRegistryKit, setSelectedRegistryKit] = useState<RegistryKit | null>(null);
  const { isLoading, isAuthenticated } = useAuth();
  
  // Get the selected kit from the store
  const getSelectedKit = useRegistryStore(state => state.getSelectedKit);

  // Save sidebar state to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('sidebarExpanded', String(sidebarExpand));
  }, [sidebarExpand]);

  const changeLeftSidebarSize = (expand: boolean) => {
    setSidebarExpand(expand);
  };

  const handleRegistryKitSelect = (kit: RegistryKit | null) => {
    console.log("ProjectInterface received kit selection:", kit?.kitConfig?.name || 'None');
    setSelectedRegistryKit(kit);
  };

  // Calculate sizes in pixels - increased expandedWidth from 240 to 280
  const expandedWidth = 280;
  const collapsedWidth = 56;
  const currentWidth = sidebarExpand ? expandedWidth : collapsedWidth;

  // Handle loading and authentication check before rendering main layout
  if (isLoading) {
    return <div className="h-screen flex items-center justify-center bg-background">

<img src="/logo.png" alt="Genbase Logo" className="h-20 w-20" />
    </div>;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    console.log("Not authenticated");
  }

  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <div className="h-screen flex flex-col bg-background text-foreground">
        {/* Fixed-width sidebar approach instead of using ResizablePanelGroup */}
        <div className="flex-1 flex relative">
          {/* Fixed-width sidebar with transition */}
          <div 
            className="h-full transition-all duration-300 ease-in-out border-r border-border"
            style={{ 
              width: `${currentWidth}px`,
              minWidth: `${currentWidth}px`, 
              maxWidth: `${currentWidth}px`,
              overflow: 'hidden'
            }}
          >
            <LeftSidebar
              onExpand={changeLeftSidebarSize}
              expanded={sidebarExpand}
              onRegistryKitSelect={handleRegistryKitSelect}
            />
          </div>
          
          {/* Main content area */}
          <div className="flex-1 h-full overflow-hidden bg-background relative">
            <Routes>
              <Route path="/" element={<Navigate to="/modules" replace />} />
              <Route path="/modules/*" element={<ModuleLayout />} />
              <Route
                path="/registry/*"
                element={<RegistryPage selectedKit={getSelectedKit() || selectedRegistryKit} />}
              />
              <Route path="/settings" element={<SettingsLayout />}>
                <Route index element={<Navigate to="model" replace />} />
                <Route path="model" element={<ModelSettings />} />
                <Route path="security" element={<PasswordResetPage />} />
              </Route>
              <Route
                path="/users/*"
                element={
                  <SuperuserRoute>
                    <UserManagementPage />
                  </SuperuserRoute>
                }
              />
              <Route path="*" element={
                <div className="h-full flex items-center justify-center bg-background">
                  <h2 className="text-xl text-muted-foreground">404 - Page Not Found</h2>
                </div>
              } />
            </Routes>
          </div>
        </div>
      </div>
      <Toaster/>
    </ThemeProvider>
  );
};

export default App;