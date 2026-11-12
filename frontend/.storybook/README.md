# Storybook Documentation

Welcome to the L30 component library documentation powered by Storybook.

## Overview

This Storybook instance provides interactive documentation for L30 UI components. Each component includes:

- **Interactive examples** with controls to modify props
- **Usage guidelines** and best practices
- **Accessibility notes** and WCAG compliance information
- **Multiple variants and states**
- **Code examples** showing how to use components
- **Brand voice guidelines** for text-based components

## Running Storybook

### Development Mode

Start Storybook in development mode with hot reloading:

```bash
npm run storybook
```

This will start Storybook at [http://localhost:6006](http://localhost:6006)

### Building Storybook

Build a static version of Storybook for deployment:

```bash
npm run build-storybook
```

The static files will be output to `storybook-static/`.

## Component Organization

Stories are organized into the following categories:

### **Loading**
Skeleton components for loading states:
- `Skeleton Table` - Table loading skeletons
- `Skeleton Table Compact` - Compact table skeletons
- `Staff Stats Cards` - Dashboard stats loading
- `Staff List` - List loading states
- `Staff Page With Tabs` - Complete page skeletons
- `Staff Dashboard Panel` - Panel skeletons

### **Forms**
Form-related components:
- `Form Error` - Error messages
- `Form Helper` - Helper text
- `Form Success` - Success indicators
- `Validated Input` - Input with validation

### **Feedback**
User feedback components:
- `Empty State` - Empty state displays
- `Empty State Card` - Card variant
- `Empty State Inline` - Inline variant
- `Error Alert` - Error messages with actions
- `Error Alert Compact` - Compact error messages
- `Network Error` - Network connectivity errors
- `Offline Indicator` - Offline status banner

### **Components**
Core UI components:
- `Button` - Primary/secondary/tertiary/danger buttons
- `IconButton` - Icon-only buttons
- `Modal` - Dialog modals
- `StatCard` - Statistics cards

### **Accessibility**
Accessibility feature components:
- `Preset Selector` - Accessibility presets
- `Keyboard Shortcuts` - Keyboard shortcut overlay
- `Contrast Checker` - Color contrast tool
- `Settings Export Import` - Settings management
- `Onboarding Wizard` - Accessibility onboarding
- `Content Complexity` - Content difficulty indicators
- `Bionic Text` - Bionic reading format
- `Quick Widget` - Quick accessibility widget

## Writing New Stories

### Story File Structure

Create a new story file with the `.stories.tsx` extension:

```tsx
import type { Meta, StoryObj } from '@storybook/react';
import { YourComponent } from './YourComponent';

const meta: Meta<typeof YourComponent> = {
  title: 'Category/Component Name',
  component: YourComponent,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded', // or 'centered', 'fullscreen'
    docs: {
      description: {
        component: `
Component description here...

**Features:**
- Feature 1
- Feature 2

**Use Cases:**
- Use case 1
- Use case 2
        `,
      },
    },
  },
  argTypes: {
    // Define controls for props
    variant: {
      control: 'select',
      options: ['primary', 'secondary'],
    },
  },
};

export default meta;

type Story = StoryObj<typeof YourComponent>;

export const Default: Story = {
  args: {
    // Default props
  },
};

export const Variant: Story = {
  args: {
    // Different props
  },
  parameters: {
    docs: {
      description: {
        story: 'Description of this specific story',
      },
    },
  },
};
```

### CSF 3.0 Format

We use [Component Story Format (CSF) 3.0](https://storybook.js.org/docs/react/api/csf) which provides:

- TypeScript support out of the box
- Better type inference
- Simplified story syntax
- Auto-generated documentation

### Best Practices

1. **Component Documentation**
   - Write clear descriptions explaining what the component does
   - List all features and capabilities
   - Include use cases and examples
   - Document accessibility features

2. **Story Variants**
   - Show all component variants (colors, sizes, states)
   - Include edge cases (loading, error, disabled, empty)
   - Demonstrate interactive features
   - Show responsive behavior when applicable

3. **Accessibility**
   - Note ARIA attributes and keyboard navigation
   - Mention WCAG compliance level
   - Document screen reader behavior
   - Include focus management notes

4. **Brand Voice**
   - For text-based components, show brand voice examples
   - Demonstrate warm, helpful, encouraging messaging
   - Include examples of error messages with recovery actions

5. **Interactive Examples**
   - Use `argTypes` to expose controls
   - Create realistic, practical examples
   - Show components in context when helpful
   - Include combination/composition examples

## Addons Available

### Essentials
- **Controls**: Dynamically interact with component props
- **Actions**: View component event handlers
- **Viewport**: Test responsive designs
- **Backgrounds**: Test on different backgrounds
- **Toolbars**: Theme and direction switching

### Accessibility (a11y)
- Automatic accessibility testing
- WCAG compliance checks
- Color contrast verification
- ARIA attribute validation

Enable the a11y panel in Storybook to see accessibility violations.

### Interactions
- Test user interactions
- Play functions for automated testing
- Step-by-step interaction debugging

## Theme Support

Stories support light/dark mode and RTL/LTR direction switching via the toolbar:

- **Theme**: Switch between light, dark, and high-contrast modes
- **Direction**: Toggle between LTR and RTL text direction

These settings are configured in `.storybook/preview.tsx`.

## Testing Stories

Stories can be used as test fixtures:

```tsx
import { composeStories } from '@storybook/react';
import * as stories from './YourComponent.stories';

const { Default, Variant } = composeStories(stories);

test('renders default story', () => {
  render(<Default />);
  // assertions...
});
```

## File Locations

- **Story files**: `src/**/*.stories.tsx`
- **Storybook config**: `.storybook/main.ts`
- **Preview config**: `.storybook/preview.tsx`
- **This README**: `.storybook/README.md`

## Storybook Configuration

### main.ts

Configures story file patterns, addons, and framework:

- Stories: `../src/**/*.stories.@(js|jsx|mjs|ts|tsx)`
- Framework: `@storybook/react-vite`
- Addons: essentials, interactions, a11y, links

### preview.tsx

Configures global settings:

- CSS imports
- Theme decorator
- Accessibility settings
- Background options
- Global toolbar items

## Resources

- [Storybook Documentation](https://storybook.js.org/docs/react/get-started/introduction)
- [CSF 3.0 Guide](https://storybook.js.org/docs/react/api/csf)
- [Accessibility Addon](https://storybook.js.org/addons/@storybook/addon-a11y)
- [Writing Stories](https://storybook.js.org/docs/react/writing-stories/introduction)

## Contributing

When adding new components:

1. Create a `.stories.tsx` file alongside your component
2. Follow the story file structure above
3. Include all variants and states
4. Add accessibility notes
5. Write clear documentation
6. Test in Storybook before committing

## Support

For questions about Storybook or component documentation:

- Check the [Storybook docs](https://storybook.js.org/docs)
- Review existing story files for examples
- Ask the development team

---

**Last Updated**: February 2026
**Storybook Version**: 8.6.14
**Framework**: React 18 + Vite 7
