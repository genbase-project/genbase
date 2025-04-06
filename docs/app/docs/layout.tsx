import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { baseOptions } from '@/app/layout.config';
import { source } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return (
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
  <DocsLayout tree={source.pageTree} {...baseOptions}>
  {children}
</DocsLayout>
  );
}




