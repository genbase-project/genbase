import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
/**
 * Shared layout configurations
 *
 * you can configure layouts individually from:
 * Home Layout: app/(home)/layout.tsx
 * Docs Layout: app/docs/layout.tsx
 */
export const baseOptions: BaseLayoutProps = {
  nav: {
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
    title: 'Genbase'
  },
  links: [
    {
      text: 'Documentation',
      url: '/docs',
      active: 'nested-url',
    },
  ],
};
