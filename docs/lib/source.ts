import { docs, meta } from '@/.source';
import { createMDXSource } from 'fumadocs-mdx';
import { loader } from 'fumadocs-core/source';
import { createOpenAPI } from 'fumadocs-openapi/server';
// import { attachFile } from 'fumadocs-openapi/server';

export const source = loader({
  baseUrl: '/docs',
  source: createMDXSource(docs, meta),
  // pageTree: { //for api reference
  //   attachFile,
  // },
});

 
export const openapi = createOpenAPI();