import { Redirect, Stack } from "expo-router";

import { useAuth } from "../../src/auth/AuthContext";
import { colors } from "../../src/theme";

export default function SettingsLayout() {
  const { state } = useAuth();
  if (state.status === "signedOut") return <Redirect href="/welcome" />;
  return (
    <Stack screenOptions={{ headerShown: true, headerTintColor: colors.text, headerStyle: { backgroundColor: colors.background }, contentStyle: { backgroundColor: colors.background } }}>
      <Stack.Screen name="edit" options={{ title: "Профиль" }} />
      <Stack.Screen name="address" options={{ title: "Мой адрес" }} />
      <Stack.Screen name="devices" options={{ title: "Устройства" }} />
      <Stack.Screen name="data" options={{ title: "Мои данные" }} />
      <Stack.Screen name="delete" options={{ title: "Удаление аккаунта" }} />
    </Stack>
  );
}
