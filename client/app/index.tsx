import { Redirect } from "expo-router";
import { ActivityIndicator, Image, StyleSheet, View } from "react-native";

import { LOGO } from "../src/assets";
import { useAuth } from "../src/auth/AuthContext";
import { colors } from "../src/theme";

export default function Index() {
  const { state } = useAuth();
  if (state.status === "loading") {
    return (
      <View style={styles.center} testID="splash">
        <Image source={LOGO} style={styles.logo} />
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  return <Redirect href={state.status === "signedIn" ? "/home" : "/welcome"} />;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 16, backgroundColor: colors.background },
  logo: { width: 96, height: 96 },
});
