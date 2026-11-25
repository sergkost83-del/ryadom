import { StyleSheet, Text, TextInput, View, type KeyboardTypeOptions } from "react-native";

import { colors, radius, spacing } from "../theme";

interface Props {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  error?: string | null;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  maxLength?: number;
  testID?: string;
  large?: boolean;
}

export function TextField({ label, value, onChangeText, error, placeholder, keyboardType, autoCapitalize, maxLength, testID, large }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        maxLength={maxLength}
        accessibilityLabel={label}
        style={[styles.input, large && styles.large, !!error && styles.inputError]}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { color: colors.textMuted, fontSize: 14, fontWeight: "600" },
  input: { borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, borderRadius: radius.m, paddingHorizontal: spacing.l, paddingVertical: 12, fontSize: 17, color: colors.text },
  large: { fontSize: 26, letterSpacing: 6, textAlign: "center" },
  inputError: { borderColor: colors.danger },
  error: { color: colors.danger, fontSize: 13 },
});
