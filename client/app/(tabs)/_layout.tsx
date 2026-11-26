import { Redirect, Tabs } from "expo-router";
import { ActivityIndicator, View } from "react-native";

import { useAuth } from "../../src/auth/AuthContext";
import { colors } from "../../src/theme";

export default function TabsLayout() {
  const { state } = useAuth();
  if (state.status === "loading") {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  if (state.status === "signedOut") return <Redirect href="/welcome" />;
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: colors.primary, tabBarLabelStyle: { fontSize: 13, fontWeight: "700" } }}>
      <Tabs.Screen name="home" options={{ title: "Главная" }} />
      <Tabs.Screen name="chats" options={{ title: "Чаты" }} />
      <Tabs.Screen name="profile" options={{ title: "Профиль" }} />
    </Tabs>
  );
}
