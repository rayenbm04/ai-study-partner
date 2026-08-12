import { TextClassContext } from '@/components/ui/text';
import { cn } from '@/lib/utils';
import type { Icon as PhosphorIcon, IconProps as PhosphorIconProps } from 'phosphor-react-native';
import { cssInterop } from 'nativewind';
import * as React from 'react';

type IconProps = PhosphorIconProps & {
  className?: string;
  as: PhosphorIcon;
} & React.RefAttributes<PhosphorIcon>;

function IconImpl({ as: IconComponent, ...props }: IconProps) {
  // cssInterop rewrites `className` into a `style` prop at runtime before
  // this renders, but Phosphor's own IconProps type doesn't declare
  // `className` — cast away the excess property the interop consumes.
  return <IconComponent {...(props as PhosphorIconProps)} />;
}

cssInterop(IconImpl, {
  className: {
    target: 'style',
    nativeStyleToProp: {
      height: 'size',
      width: 'size',
    },
  },
});

/**
 * A wrapper component for Phosphor icons with Nativewind `className` support via `cssInterop`.
 *
 * This component allows you to render any Phosphor icon while applying utility classes
 * using `nativewind`. It avoids the need to wrap or configure each icon individually.
 *
 * @component
 * @example
 * ```tsx
 * import { ArrowRight } from 'phosphor-react-native';
 * import { Icon } from '@/components/ui/icon';
 *
 * <Icon as={ArrowRight} className="text-red-500" size={16} />
 * ```
 *
 * @param {PhosphorIcon} as - The Phosphor icon component to render.
 * @param {string} className - Utility classes to style the icon using Nativewind.
 * @param {number} size - Icon size (defaults to 14).
 * @param {...PhosphorIconProps} ...props - Additional Phosphor icon props passed to the "as" icon.
 */
function Icon({ as: IconComponent, className, size = 14, ...props }: IconProps) {
  const textClass = React.useContext(TextClassContext);
  return (
    <IconImpl
      as={IconComponent}
      className={cn('text-foreground', textClass, className)}
      size={size}
      {...props}
    />
  );
}

export { Icon };
