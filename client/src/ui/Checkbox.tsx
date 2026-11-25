import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, spacing } from "../theme";

interface Props {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  testID?: string;
  linkText?: string;
  onLinkPress?: () => void;
}

export function Checkbox({ checked, onChange, label, testID, linkText, onLinkPress }: Props) {
  return (
    <View style={styles.row}>
      <Pressable testID={testID} accessibilityRole="checkbox" accessibilityState={{ checked }} onPress={() => onChange(!checked)} style={[styles.box, checked && styles.boxChecked]}>
        {checked ? <Text style={styles.tick}>✓</Text> : null}
      </Pressable>
      <Text style={styles.label} onPress={() => onChange(!checked)}>
        {label}
        {linkText ? (
          <Text style={styles.link} onPress={onLinkPress}>
            {" "}
            {linkText}
          </Text>
        ) : null}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: spacing.m, alignItems: "flex-start" },
  box: { width: 26, height: 26, borderRadius: 8, borderWidth: 2, borderColor: colors.border, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" },
  boxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  tick: { color: "#FFFFFF", fontWeight: "800" },
  label: { flex: 1, color: colors.text, fontSize: 15, lineHeight: 21 },
  link: { color: colors.primary, fontWeight: "700" },
});
