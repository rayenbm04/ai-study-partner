/**
 * Local (on-device) daily study reminder — no push server exists for this
 * app, so this uses expo-notifications' local scheduling, which needs
 * nothing but OS permission. One fixed time (REMINDER_HOUR:00) rather than a
 * time picker, to keep the feature to a single on/off toggle in Settings.
 */
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

import { storage } from "./storage";

const REMINDER_ENABLED_KEY = "daily_reminder_enabled";
const REMINDER_NOTIFICATION_ID_KEY = "daily_reminder_notification_id";
export const REMINDER_HOUR = 18;

export async function isDailyReminderEnabled(): Promise<boolean> {
  return (await storage.getItem(REMINDER_ENABLED_KEY)) === "true";
}

/** Requests OS notification permission if needed, schedules the daily
 * reminder, and persists both the toggle state and the scheduled
 * notification's id (so it can be cancelled later). Returns false — without
 * enabling — if permission was denied. */
export async function enableDailyReminder(title: string, body: string): Promise<boolean> {
  if (Platform.OS === "web") return false; // expo-notifications has no local-scheduling support on web

  const { status: existing } = await Notifications.getPermissionsAsync();
  let granted = existing === "granted";
  if (!granted) {
    const { status } = await Notifications.requestPermissionsAsync();
    granted = status === "granted";
  }
  if (!granted) return false;

  const previousId = await storage.getItem(REMINDER_NOTIFICATION_ID_KEY);
  if (previousId) await Notifications.cancelScheduledNotificationAsync(previousId).catch(() => {});

  const id = await Notifications.scheduleNotificationAsync({
    content: { title, body },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: REMINDER_HOUR, minute: 0 },
  });

  await storage.setItem(REMINDER_NOTIFICATION_ID_KEY, id);
  await storage.setItem(REMINDER_ENABLED_KEY, "true");
  return true;
}

export async function disableDailyReminder(): Promise<void> {
  const id = await storage.getItem(REMINDER_NOTIFICATION_ID_KEY);
  if (id) await Notifications.cancelScheduledNotificationAsync(id).catch(() => {});
  await storage.setItem(REMINDER_ENABLED_KEY, "false");
}
