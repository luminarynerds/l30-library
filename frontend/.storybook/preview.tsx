import type { Preview } from '@storybook/react';
import '../src/index.css';

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      // Enable accessibility addon
      element: '#storybook-root',
      config: {},
      options: {},
      manual: false,
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#F9F6F0' },
        { name: 'dark', value: '#1a1a1a' },
        { name: 'white', value: '#ffffff' },
      ],
    },
  },
  globalTypes: {
    theme: {
      name: 'Theme',
      description: 'Global theme for components',
      defaultValue: 'light',
      toolbar: {
        icon: 'circlehollow',
        items: ['light', 'dark', 'high-contrast'],
        showName: true,
      },
    },
    direction: {
      name: 'Direction',
      description: 'Text direction',
      defaultValue: 'ltr',
      toolbar: {
        icon: 'transfer',
        items: ['ltr', 'rtl'],
        showName: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme || 'light';
      const direction = context.globals.direction || 'ltr';

      // Apply theme class to root
      document.documentElement.classList.remove('light', 'dark', 'high-contrast');
      document.documentElement.classList.add(theme);
      document.documentElement.setAttribute('dir', direction);

      return <Story />;
    },
  ],
};

export default preview;
