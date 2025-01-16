import React from 'react';
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PackageOpen, GitFork, Network } from 'lucide-react';
import { UncontrolledTreeEnvironment, Tree, StaticTreeDataProvider } from 'react-complex-tree';
import { codeTreeItems } from '../../data/treeData';

interface RightSidebarProps {
  rightTab: string;
  setRightTab: (tab: string) => void;
}

const RightSidebar: React.FC<RightSidebarProps> = ({ rightTab, setRightTab }) => {
  return (
    <div className="h-full border-l border-gray-800 flex flex-col">
      <TooltipProvider>
        <div className="flex justify-around items-center p-2 border-b border-gray-800">
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'dependencies' ? 'bg-gray-800' : ''}
                onClick={() => setRightTab('dependencies')}
              >
                <PackageOpen className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependencies</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'dependants' ? 'bg-gray-800' : ''}
                onClick={() => setRightTab('dependants')}
              >
                <GitFork className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Dependants</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger>
              <Button 
                variant="ghost" 
                size="icon"
                className={rightTab === 'context' ? 'bg-gray-800' : ''}
                onClick={() => setRightTab('context')}
              >
                <Network className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Context</TooltipContent>
          </Tooltip>
        </div>
      </TooltipProvider>

      <div className="flex-1 overflow-auto">
        <UncontrolledTreeEnvironment
          dataProvider={new StaticTreeDataProvider(codeTreeItems, (item, data) => ({ ...item, data }))}
          getItemTitle={item => item.data}
          viewState={{}}
        >
          <Tree treeId="right-tree" rootItem="root" treeLabel="Dependencies" />
        </UncontrolledTreeEnvironment>
      </div>
    </div>
  );
};

export default RightSidebar;