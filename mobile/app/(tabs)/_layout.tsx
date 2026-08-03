import { Tabs } from "expo-router";

import { AppTabBar } from "../../components/AppTabBar";

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <AppTabBar {...props} />}>
      <Tabs.Screen name="index" options={{ title: "Accueil" }} />
      <Tabs.Screen name="cards" options={{ title: "Cartes" }} />
      <Tabs.Screen name="study-plan" options={{ title: "Plan" }} />
      <Tabs.Screen name="progress" options={{ title: "Progrès" }} />
      <Tabs.Screen name="settings" options={{ title: "Réglages" }} />
    </Tabs>
  );
}
