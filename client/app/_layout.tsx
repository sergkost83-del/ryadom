import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { AuthProvider } from "../src/auth/AuthContext";
import { colors } from "../src/theme";

export default function RootLayout() {
  return (
    <AuthProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
        <Stack.Screen name="legal/[type]" options={{ headerShown: true, title: "Документ" }} />
        <Stack.Screen name="chat/[id]" options={{ headerShown: true, title: "Чат" }} />
      </Stack>
    </AuthProvider>
  );
}
