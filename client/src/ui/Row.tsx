import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../theme";

interface Props {
  title: string;
  subtitle?: string;
  onPress: () => void;
  danger?: boolean;
  testID?: string;
}

export function Row({ title, subtitle, onPress, danger = false, testID }: Props) {
  return (
    <Pressable accessibilityRole="button" testID={testID} onPress={onPress} style={styles.row}>
      <View style={styles.texts}>
        <Text style={[styles.title, danger && { color: colors.danger }]}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      <Text style={styles.chevron}>›</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", backgroundColor: colors.surface, borderRadius: radius.m, borderWidth: 1, borderColor: colors.border, padding: spacing.l },
  texts: { flex: 1, gap: 2 },
  title: { fontSize: 16, fontWeight: "700", color: colors.text },
  subtitle: { fontSize: 13, color: colors.textMuted },
  chevron: { fontSize: 24, color: colors.textMuted },
});
