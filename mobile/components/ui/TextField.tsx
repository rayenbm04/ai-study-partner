import { View, type TextInputProps } from "react-native";

import { cn } from "../../lib/utils";
import { Input } from "./input";
import { Text } from "./text";

export function TextField({
  label,
  error,
  style,
  className,
  multiline,
  ...props
}: TextInputProps & { label?: string; error?: string | null; className?: string }) {
  return (
    <View style={style}>
      {label ? <Text className="mb-1.5 ml-1 text-sm font-medium text-muted-foreground">{label}</Text> : null}
      <Input
        multiline={multiline}
        aria-invalid={!!error}
        className={cn(multiline && "h-24 py-2", className)}
        {...props}
      />
      {error ? <Text className="mt-1 ml-1 text-xs text-destructive">{error}</Text> : null}
    </View>
  );
}
