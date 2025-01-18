import React, { useState, useRef } from 'react';
import { Allotment, AllotmentHandle } from "allotment";
import "allotment/dist/style.css";
import 'react-complex-tree/lib/style-modern.css';
import Header from './components/layout/Header';
import LeftSidebar from './components/layout/LeftSidebar';
import MainContent from './components/layout/MainContent';
import RightSidebar from './components/layout/RightSidebar';
import BottomPanel from './components/layout/BottomPanel';
import { useRuntimeModuleStore } from './store';

const ProjectInterface = () => {
  const [activeMainTab, setActiveMainTab] = useState('code');
  const [rightTab, setRightTab] = useState('');
  const rightAllotmentRef = useRef<AllotmentHandle>(null);
  const selectedModule = useRuntimeModuleStore(state => state.selectedModule);

  const handleRightTabChange = (tab: string) => {
    if (rightTab === tab) {
      setRightTab('');
      rightAllotmentRef.current?.resize([250, 700, 48]);
    } else {
      setRightTab(tab);
      rightAllotmentRef.current?.resize([250, 500, 250]);
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
              <Allotment ref={rightAllotmentRef} defaultSizes={[250, 700, 48]}>
                <Allotment.Pane minSize={200}>
                  <MainContent 
                    selectedModule={selectedModule}
                  />
                </Allotment.Pane>

                <Allotment.Pane minSize={48} maxSize={300} snap>
                  <RightSidebar 
                    rightTab={rightTab}
                    setRightTab={handleRightTabChange}
                    selectedModule={selectedModule}
                  />
                </Allotment.Pane>
              </Allotment>

              <Allotment.Pane minSize={100} preferredSize={100}>
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
