import { Tabs } from "expo-router";

import { AppTabBar } from "../../components/AppTabBar";
import { useLanguage } from "../../lib/language-context";

export default function TabsLayout() {
  const { t } = useLanguage();

  return (
    <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <AppTabBar {...props} />}>
      <Tabs.Screen name="index" options={{ title: t("tabs.home") }} />
      <Tabs.Screen name="cards" options={{ title: t("tabs.cards") }} />
      <Tabs.Screen name="study-plan" options={{ title: t("tabs.studyPlan") }} />
      <Tabs.Screen name="progress" options={{ title: t("tabs.progress") }} />
      <Tabs.Screen name="settings" options={{ title: t("tabs.settings") }} />
    </Tabs>
  );
}
