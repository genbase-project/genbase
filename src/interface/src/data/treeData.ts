export const mainTreeItems = {
    root: {
      index: 'root',
      isFolder: true,
      children: ['services'],
      data: 'Root',
    },
    services: {
      index: 'services',
      isFolder: true,
      children: ['frontend'],
      data: 'services',
    },
    frontend: {
      index: 'frontend',
      isFolder: true,
      children: ['pages', 'components'],
      data: 'Frontend',
    },
  };
  
  export const codeTreeItems = {
    root: {
      index: 'root',
      isFolder: true,
      children: ['folder1', 'folder2'],
      data: 'Structure',
    },
    folder1: {
      index: 'folder1',
      isFolder: true,
      children: ['config1', 'config2'],
      data: 'folder 1',
    },
    folder2: {
      index: 'folder2',
      isFolder: true,
      children: ['codefile1'],
      data: 'folder 2',
    },
    config1: {
      index: 'config1',
      children: [],
      data: 'config 1',
    },
    config2: {
      index: 'config2',
      children: [],
      data: 'config 2',
    },
    codefile1: {
      index: 'codefile1',
      children: [],
      data: 'code file 1',
    },
  };