import React, { useState, useRef } from 'react';
import { Allotment, AllotmentHandle } from "allotment";
import "allotment/dist/style.css";
import 'react-complex-tree/lib/style-modern.css';
import Header from './layout/Header';
import LeftSidebar from './layout/LeftSidebar';
import MainContent from './layout/MainContent';
import RightSidebar from './layout/RightSidebar';
import BottomPanel from './layout/BottomPanel';
import { useModuleStore } from './store';
import { GripHorizontal } from 'lucide-react';

const ProjectInterface = () => {
  const [activeMainTab, setActiveMainTab] = useState('code');
  const [rightTab, setRightTab] = useState('');
  const rightAllotmentRef = useRef<AllotmentHandle>(null);
  const selectedModule = useModuleStore(state => state.selectedModule);

  const handleRightTabChange = (tab: string) => {
    if (rightTab === tab) {
      setRightTab('');
      rightAllotmentRef.current?.resize([250, 700, 48]); // Use 48px for icon-only width
    } else {
      setRightTab(tab);
      rightAllotmentRef.current?.resize([250, 450, 300]); // Adjust middle and right panel sizes
    }
  };
  

  return (
    <div className="h-screen flex flex-col bg-background">
      <Header />
      
      <Allotment vertical className="flex-1">
        <Allotment.Pane>
          <Allotment>
            <Allotment.Pane minSize={200} maxSize={300}>
              <LeftSidebar />
            </Allotment.Pane>

            <Allotment vertical className="flex-1">
            <Allotment ref={rightAllotmentRef} defaultSizes={[250, 700, 54]}>
  <Allotment.Pane minSize={200}>
    <MainContent 
      selectedModule={selectedModule}
    />
  </Allotment.Pane>

  <Allotment.Pane minSize={rightTab==''?54:300} maxSize={rightTab==''?54:400} preferredSize={rightTab==''?54:300} snap>
    <RightSidebar 
      rightTab={rightTab}
      setRightTab={handleRightTabChange}
      selectedModule={selectedModule}
    />
  </Allotment.Pane>
</Allotment>


              <Allotment.Pane  maxSize={1000}>


                      <div 
                  className="absolute top-0 left-0 right-0 h-3 z-10 cursor-row-resize flex items-center justify-center bg-white/50"
                 
                >
                 <GripHorizontal className="h-3 w-3 text-gray-400" />
                </div>
                <BottomPanel 
                selectedModule={selectedModule}
                 />
              </Allotment.Pane>
            </Allotment>
          </Allotment>
        </Allotment.Pane>
      </Allotment>
    </div>
  );
};

export default ProjectInterface;
