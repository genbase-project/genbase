import { useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import 'react-complex-tree/lib/style-modern.css';
import LeftSidebar from './layout/LeftSidebar';
import MainContentContainer from './MainContentContainer';
import { ThemeProvider } from './components/themeProvider';

const ProjectInterface = () => {
  const [sidebarExpand, setSidebarExpand] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("modules");
  
  const changeLeftSidebarSize = (expand: boolean) => {
    setSidebarExpand(expand);
  };

  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <div className="h-screen flex flex-col bg-background">
        <ResizablePanelGroup direction="horizontal" className="flex-1 relative">
          {/* Increase the size to accommodate both the narrow sidebar and expanded content */}
          <ResizablePanel 
            minSize={sidebarExpand ? 25 : 4} 
            maxSize={sidebarExpand ? 25 : 4} 
            defaultSize={sidebarExpand ? 25 : 4}
            className="z-10" // Ensure sidebar is above other content
          >
            <LeftSidebar 
              onExpand={changeLeftSidebarSize} 
              expanded={sidebarExpand} 
              onTabChange={setActiveTab}
            />
          </ResizablePanel>
          <ResizableHandle withHandle className="z-10" /> {/* Ensure handle is visible */}
          <ResizablePanel className="z-0">
            <MainContentContainer activeTab={activeTab} />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </ThemeProvider>
  );
};

export default ProjectInterface;