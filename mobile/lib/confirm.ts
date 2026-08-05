/** Cross-platform confirm dialog for destructive actions.
 *
 * react-native-web's `Alert.alert()` is a complete no-op (see
 * node_modules/react-native-web/src/exports/Alert — the whole implementation
 * is `static alert() {}`), so a plain `Alert.alert(...)` silently does
 * nothing on web: no dialog, no callback ever fires. `window.confirm` is the
 * real cross-platform equivalent there. */
import { Alert, Platform } from "react-native";

export function confirmDestructiveAction(title: string, message: string, confirmLabel = "Delete"): Promise<boolean> {
  if (Platform.OS === "web") {
    return Promise.resolve(window.confirm(`${title}\n\n${message}`));
  }
  return new Promise((resolve) => {
    Alert.alert(title, message, [
      { text: "Cancel", style: "cancel", onPress: () => resolve(false) },
      { text: confirmLabel, style: "destructive", onPress: () => resolve(true) },
    ]);
  });
}
