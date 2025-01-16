import React from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus } from 'lucide-react';
import { UncontrolledTreeEnvironment, Tree, StaticTreeDataProvider } from 'react-complex-tree';
import { mainTreeItems } from '../../data/treeData';


const LeftSidebar = () => {
  return (
    <div className="h-full bg-background border-r border-gray-800 flex flex-col">
      <div className="flex items-center p-2 border-b border-gray-800 shrink-0">
        <Input className="h-8 bg-background-secondary border-gray-800" placeholder="Search" />
        <Button variant="ghost" size="icon" className="ml-2">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="overflow-auto flex-1">
        <UncontrolledTreeEnvironment
          dataProvider={new StaticTreeDataProvider(mainTreeItems, (item, data) => ({ ...item, data }))}
          getItemTitle={item => item.data}
          viewState={{}}
        >
          <Tree treeId="main-tree" rootItem="root" treeLabel="Project Structure" />
        </UncontrolledTreeEnvironment>
      </div>
    </div>
  );
};

export default LeftSidebar;