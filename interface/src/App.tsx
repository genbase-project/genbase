import React, { useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,

} from "@/components/ui/resizable";
import 'react-complex-tree/lib/style-modern.css';
import LeftSidebar from './layout/LeftSidebar';
import MainContent from './layout/MainContent';
import RightSidebar from './layout/RightSidebar';
import BottomPanel from './layout/BottomPanel';
import { useModuleStore } from './store';
import { GripHorizontal } from 'lucide-react';
import { ThemeProvider } from './components/themeProvider';

const ProjectInterface = () => {
  const [rightTab, setRightTab] = useState('');
  const [sidebarExpand, setSidebarExpand] = useState(true);
  const selectedModule = useModuleStore(state => state.selectedModule);

  
  const changeLeftSidebarSize = (expand: boolean) => {
    console.log(expand);
    setSidebarExpand(expand);
  };


  


  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
    <div className="h-screen flex flex-col bg-background">

      
      <ResizablePanelGroup direction="horizontal" className="flex-1">
      
         <ResizablePanel   minSize={sidebarExpand? 20:4} maxSize={sidebarExpand? 20:4} >
          <LeftSidebar onExpand={changeLeftSidebarSize} expanded={sidebarExpand} />
          </ResizablePanel>
      
        <ResizableHandle />
        <ResizablePanel>
          <ResizablePanelGroup direction="vertical">
            <ResizablePanel defaultSize={75}>
              <MainContent selectedModule={selectedModule} />
            </ResizablePanel>
            <ResizableHandle withHandle>
              <div className="flex h-full w-full items-center justify-center">
                <GripHorizontal className="h-3 w-3 text-gray-400" />
              </div>
            </ResizableHandle>
            <ResizablePanel defaultSize={25} minSize={10} maxSize={95}>
              <BottomPanel selectedModule={selectedModule} />
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>
    
    </div>
   </ThemeProvider>
  );
};

export default ProjectInterface;
