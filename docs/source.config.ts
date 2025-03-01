import { defineDocs, defineConfig } from 'fumadocs-mdx/config';
import { remarkMermaid } from '@theguild/remark-mermaid';

import { remarkImage } from 'fumadocs-core/mdx-plugins';

export const { docs, meta } = defineDocs({
  dir: 'content/docs',
});

export default defineConfig({
  mdxOptions: {
    remarkPlugins: [remarkMermaid, remarkImage],
  },
});

