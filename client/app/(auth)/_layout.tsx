import { Redirect, Stack } from "expo-router";

import { useAuth } from "../../src/auth/AuthContext";
import { colors } from "../../src/theme";

export default function AuthLayout() {
  const { state } = useAuth();
  if (state.status === "signedIn") return <Redirect href="/home" />;
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }} />;
}
