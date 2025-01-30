export interface TreeItem {
    index: string;
    isFolder?: boolean;
    children: string[];
    data: string;
  }
  
  export interface TreeItems {
    [key: string]: TreeItem;
  }
  
  export type TabType = 'code' | 'human explanation' | 'specification' | 'data views' | 'access' | 'custom';
  export type RightTabType = 'dependencies' | 'dependants' | 'context';









  