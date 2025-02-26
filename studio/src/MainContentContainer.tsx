import React, { useState } from 'react';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from "@/components/ui/resizable";
import MainContent from './layout/MainContent';
import BottomPanel from './layout/BottomPanel';
import { GripHorizontal } from 'lucide-react';
import { useModuleStore } from './store';

interface MainContentContainerProps {
  activeTab: string;
}

const MainContentContainer: React.FC<MainContentContainerProps> = ({ activeTab }) => {
  const selectedModule = useModuleStore(state => state.selectedModule);
  const [isBottomPanelMaximized, setIsBottomPanelMaximized] = useState(false);
  
  // State to control the min/max sizes of panels
  const [topPanelConstraints, setTopPanelConstraints] = useState({ minSize: 30, maxSize: 90 });
  const [bottomPanelConstraints, setBottomPanelConstraints] = useState({ minSize: 10, maxSize: 70 });
  
  // Handle the toggle of maximized state
  const toggleMaximized = (maximize: boolean | ((prevState: boolean) => boolean)) => {
    setIsBottomPanelMaximized(maximize);
    
    if (maximize) {
      // First, set exact constraints to force the size
      setTopPanelConstraints({ minSize: 10, maxSize: 10 });  // Smaller top panel
      setBottomPanelConstraints({ minSize: 90, maxSize: 90 });  // Larger bottom panel
      
      // Then, after a short delay, restore flexibility
      setTimeout(() => {
        setTopPanelConstraints({ minSize: 5, maxSize: 30 });  // Allow minimal flexibility at the top
        setBottomPanelConstraints({ minSize: 70, maxSize: 95 });  // Keep bottom panel large but draggable
      }, 50);
    } else {
      // First, set exact constraints to force the size
      setTopPanelConstraints({ minSize: 65, maxSize: 65 });  // Larger top panel
      setBottomPanelConstraints({ minSize: 45, maxSize: 45 });  // More visible bottom panel
      
      // Then, after a short delay, restore flexibility
      setTimeout(() => {
        setTopPanelConstraints({ minSize: 25, maxSize: 90 });  // Flexible top
        setBottomPanelConstraints({ minSize: 15, maxSize: 75 });  // Ensure minimum visibility for bottom
      }, 50);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "modules":
        return (
          <ResizablePanelGroup direction="vertical">
            <ResizablePanel 
              defaultSize={isBottomPanelMaximized ? 10 : 65}
              minSize={topPanelConstraints.minSize} 
              maxSize={topPanelConstraints.maxSize}
            >
              <MainContent selectedModule={selectedModule} />
            </ResizablePanel>
            <ResizableHandle withHandle>
              <div className="flex h-full w-full items-center justify-center">
                <GripHorizontal className="h-3 w-3 text-gray-400" />
              </div>
            </ResizableHandle>
            <ResizablePanel 
              defaultSize={isBottomPanelMaximized ? 90 : 45}
              minSize={bottomPanelConstraints.minSize} 
              maxSize={bottomPanelConstraints.maxSize}
            >
              <BottomPanel 
                selectedModule={selectedModule} 
                onMaximize={toggleMaximized}
                isMaximized={isBottomPanelMaximized}
              />
            </ResizablePanel>
          </ResizablePanelGroup>
        );
      case "registry":
        return (
          <div className="h-full flex items-center justify-center bg-black text-white">
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-semibold">Registry</h2>
              <p className="text-gray-400 max-w-md">
                The registry feature will provide a centralized repository for modules.
                This section is currently under development.
              </p>
            </div>
          </div>
        );
      default:
        return (
          <div className="h-full flex items-center justify-center bg-neutral-900">
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-semibold text-white">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h2>
              <p className="text-gray-400 max-w-md">
                This section is currently under development.
              </p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="h-full w-full">
      {renderContent()}
    </div>
  );
};

export default MainContentContainer;