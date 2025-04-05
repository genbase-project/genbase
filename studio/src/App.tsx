// src/ProjectInterface.tsx
import React, { useState } from 'react';
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
  const [sidebarExpand, setSidebarExpand] = useState(true);
  const [selectedRegistryKit, setSelectedRegistryKit] = useState<RegistryKit | null>(null);
  const { isLoading, isAuthenticated } = useAuth(); // Use auth state

  const changeLeftSidebarSize = (expand: boolean) => {
    setSidebarExpand(expand);
  };

  const handleRegistryKitSelect = (kit: RegistryKit | null) => {
    console.log("ProjectInterface received kit selection:", kit?.kitConfig?.name || 'None');
    setSelectedRegistryKit(kit);
  };

   // Handle loading and authentication check before rendering main layout
   if (isLoading) {
     return <div className="h-screen flex items-center justify-center bg-background"><p className="text-foreground">Initializing...</p></div>; // Changed to theme variables
   }

   // Redirect to login if not authenticated (adjust as needed for your login flow)
    // This might be handled better by your Router setup depending on public/private routes
   if (!isAuthenticated) {
     
         console.log("Not authenticated");
   }


  return (
    // Set default theme to light
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <div className="h-screen flex flex-col bg-background text-foreground"> {/* Changed to theme variables */}
        <ResizablePanelGroup direction="horizontal" className="flex-1 relative">
          <ResizablePanel
            minSize={sidebarExpand ? 20 : 5}
            maxSize={sidebarExpand ? 30 : 5}
            defaultSize={sidebarExpand ? 25 : 5}
            collapsible={true}
            collapsedSize={5} // Corresponds to w-14 of SidebarNav
            onCollapse={() => setSidebarExpand(false)}
            onExpand={() => setSidebarExpand(true)}
            className={`transition-all duration-300 ease-in-out ${!sidebarExpand ? 'min-w-[56px]' : ''}`} // Use pixel width for collapsed state
          >
            <LeftSidebar
              onExpand={changeLeftSidebarSize}
              expanded={sidebarExpand}
              onRegistryKitSelect={handleRegistryKitSelect}
            />
          </ResizablePanel>
          <ResizableHandle withHandle className="bg-border data-[resize-handle-state=drag]:bg-indigo-500 z-10" />
          <ResizablePanel className="z-0 bg-background"> {/* Changed to theme variable */}
             <Routes>
                {/* Redirect root or define a default authenticated route */}
                <Route path="/" element={<Navigate to="/modules" replace />} />


                {/* Authenticated routes */}
                <Route path="/modules/*" element={<ModuleLayout />} />
                <Route
                    path="/registry/*"
                    element={<RegistryPage selectedKit={selectedRegistryKit} />}
                 />
                <Route path="/settings" element={<SettingsLayout />}>
                    <Route index element={<Navigate to="model" replace />} />
                    <Route path="model" element={<ModelSettings />} />
                    <Route path="security" element={<PasswordResetPage />} />
                </Route>

                {/* Superuser-only route */}
                 <Route
                    path="/users/*"
                    element={
                        <SuperuserRoute>
                            <UserManagementPage />
                        </SuperuserRoute>
                    }
                 />

                 {/* Catch-all 404 */}
                 <Route path="*" element={
                    <div className="h-full flex items-center justify-center bg-background"> {/* Changed to theme variable */}
                         <h2 className="text-xl text-muted-foreground">404 - Page Not Found</h2> {/* Adjusted color */}
                    </div>
                } />
             </Routes>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      <Toaster/>
    </ThemeProvider>
  );
};

export default App;