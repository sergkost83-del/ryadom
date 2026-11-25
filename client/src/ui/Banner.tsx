import { StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../theme";

export function Banner({ message, kind = "error", testID }: { message: string; kind?: "error" | "info"; testID?: string }) {
  return (
    <View testID={testID} style={[styles.box, kind === "error" ? styles.error : styles.info]} accessibilityRole="alert">
      <Text style={[styles.text, { color: kind === "error" ? colors.danger : colors.text }]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { borderRadius: radius.m, padding: spacing.m },
  error: { backgroundColor: "#FDECEA" },
  info: { backgroundColor: colors.infoTint },
  text: { fontSize: 15, lineHeight: 21 },
});
