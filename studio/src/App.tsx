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
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          <ResizablePanel minSize={sidebarExpand ? 20 : 4} maxSize={sidebarExpand ? 20 : 4} defaultSize={sidebarExpand ? 20 : 4}>
            <LeftSidebar 
              onExpand={changeLeftSidebarSize} 
              expanded={sidebarExpand} 
              onTabChange={setActiveTab}
            />
          </ResizablePanel>
          <ResizableHandle />
          <ResizablePanel>
            <MainContentContainer activeTab={activeTab} />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </ThemeProvider>
  );
};

export default ProjectInterface;