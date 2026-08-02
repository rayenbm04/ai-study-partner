/**
 * Cross-platform key/value storage for auth tokens.
 *
 * expo-secure-store's web target is long-standing broken/unreliable across
 * many Expo SDK versions — it throws "getValueWithKeyAsync is not a
 * function" instead of falling back gracefully (see
 * https://github.com/expo/expo/issues/16906 and similar reports going back
 * years). Rather than wait on an upstream fix, this wrapper uses real
 * SecureStore (encrypted keychain/keystore) on iOS/Android, and
 * localStorage on web — a plain browser tab's localStorage isn't held to
 * the same "encrypted at rest" bar a mobile keychain is, but it's the
 * standard, working choice for a web session token.
 *
 * Everything else in the app (lib/api/client.ts) should go through this
 * module rather than importing expo-secure-store directly, so this is the
 * one place platform branching lives.
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") return null;
    return localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function deleteItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") return;
    localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export const storage = { getItem, setItem, deleteItem };
