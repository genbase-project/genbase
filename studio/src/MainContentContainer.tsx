import { useState, useEffect } from 'react';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from "@/components/ui/resizable";
import MainContent from './layout/MainContent';
import BottomPanel from './layout/BottomPanel';
import { GripHorizontal } from 'lucide-react';
import { useModuleStore } from './store';
import RegistryPage, { RegistryKit } from './registry/RegistryPage';


interface MainContentContainerProps {
  activeTab: string;
}

const MainContentContainer: React.FC<MainContentContainerProps> = ({ activeTab }) => {
  const selectedModule = useModuleStore(state => state.selectedModule);
  const [isBottomPanelMaximized, setIsBottomPanelMaximized] = useState(false);
  const [selectedKit, setSelectedKit] = useState<RegistryKit | null>(null);
  
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
      setBottomPanelConstraints({ minSize: 35, maxSize: 35 });  // More visible bottom panel
      
      // Then, after a short delay, restore flexibility
      setTimeout(() => {
        setTopPanelConstraints({ minSize: 25, maxSize: 90 });  // Flexible top
        setBottomPanelConstraints({ minSize: 10, maxSize: 75 });  // Ensure minimum visibility for bottom
      }, 50);
    }
  };

  // Listen for kit selection events from the sidebar
  useEffect(() => {
    const handleKitSelected = (event: CustomEvent) => {
      try {
        // Parse the stringified kit data from the event
        const kitData = JSON.parse(event.detail);
        console.log("MainContentContainer received kit:", kitData.kitConfig.name);
        setSelectedKit(kitData);
      } catch (error) {
        console.error("Error parsing kit data:", error);
      }
    };

    window.addEventListener('registry-kit-selected', handleKitSelected as EventListener);

    return () => {
      window.removeEventListener('registry-kit-selected', handleKitSelected as EventListener);
    };
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case "modules":
        return (
          <ResizablePanelGroup direction="vertical" className="h-full">
            <ResizablePanel 
              defaultSize={isBottomPanelMaximized ? 10 : 65}
              minSize={topPanelConstraints.minSize} 
              maxSize={topPanelConstraints.maxSize}
              className="h-full"
            >
              <div className="h-full overflow-hidden">
                <MainContent selectedModule={selectedModule} />
              </div>
            </ResizablePanel>
            <ResizableHandle withHandle>
              <div className="flex h-full w-full items-center justify-center">
                <GripHorizontal className="h-3 w-3 text-gray-400" />
              </div>
            </ResizableHandle>
            <ResizablePanel 
              defaultSize={isBottomPanelMaximized ? 90 : 35}
              minSize={bottomPanelConstraints.minSize} 
              maxSize={bottomPanelConstraints.maxSize}
              className="h-full"
            >
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
      case "registry":
        return <RegistryPage selectedKit={selectedKit} />;
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
    <div className="h-full w-full overflow-hidden">
      {renderContent()}
    </div>
  );
};

export default MainContentContainer;