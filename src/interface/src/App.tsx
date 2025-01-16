import React, { useState } from 'react';
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import 'react-complex-tree/lib/style-modern.css';
import Header from './components/layout/Header';
import LeftSidebar from './components/layout/LeftSidebar';
import MainContent from './components/layout/MainContent';
import RightSidebar from './components/layout/RightSidebar';
import BottomPanel from './components/layout/BottomPanel';

const ProjectInterface = () => {
  const [activeMainTab, setActiveMainTab] = useState('code');
  const [rightTab, setRightTab] = useState('dependencies');
  
  return (
    <div className="h-screen flex flex-col bg-background text-gray-300">
      <Header />
      
      <Allotment vertical className="flex-1">
        <Allotment.Pane>
          <Allotment>
            <Allotment.Pane minSize={200} preferredSize={250}>
              <LeftSidebar />
            </Allotment.Pane>

            <Allotment.Pane>
              <MainContent 
                activeMainTab={activeMainTab}
                setActiveMainTab={setActiveMainTab}
              />
            </Allotment.Pane>

            <Allotment.Pane minSize={150} preferredSize={200}>
              <RightSidebar 
                rightTab={rightTab}
                setRightTab={setRightTab}
              />
            </Allotment.Pane>
          </Allotment>
        </Allotment.Pane>

        <Allotment.Pane minSize={100} preferredSize={200}>
          <BottomPanel />
        </Allotment.Pane>
      </Allotment>
    </div>
  );
};

export default ProjectInterface;