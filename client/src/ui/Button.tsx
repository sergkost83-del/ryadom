import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { colors, radius, spacing } from "../theme";

interface Props {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "danger" | "link";
  disabled?: boolean;
  loading?: boolean;
  testID?: string;
}

export function Button({ title, onPress, variant = "primary", disabled = false, loading = false, testID }: Props) {
  const inactive = disabled || loading;
  const textColor = variant === "primary" || variant === "danger" ? "#FFFFFF" : variant === "link" ? colors.primary : colors.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive }}
      testID={testID}
      disabled={inactive}
      onPress={onPress}
      style={[styles.base, styles[variant], inactive && styles.inactive]}
    >
      {loading ? <ActivityIndicator color={textColor} /> : <Text style={[styles.text, { color: textColor }]}>{title}</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { minHeight: 50, borderRadius: radius.m, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.l },
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  danger: { backgroundColor: colors.danger },
  link: { backgroundColor: "transparent", minHeight: 40 },
  inactive: { opacity: 0.5 },
  text: { fontSize: 16, fontWeight: "700" },
});
