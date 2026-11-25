import { Image, StyleSheet, Text, View, type ImageSourcePropType } from "react-native";

import { colors, spacing } from "../theme";
import { Button } from "./Button";

interface Props {
  image: ImageSourcePropType;
  title: string;
  text?: string;
  actionTitle?: string;
  onAction?: () => void;
  testID?: string;
}

export function StateView({ image, title, text, actionTitle, onAction, testID }: Props) {
  return (
    <View style={styles.wrap} testID={testID}>
      <Image source={image} style={styles.image} resizeMode="contain" accessibilityLabel={title} />
      <Text style={styles.title}>{title}</Text>
      {text ? <Text style={styles.text}>{text}</Text> : null}
      {actionTitle && onAction ? <Button title={actionTitle} onPress={onAction} variant="secondary" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", gap: spacing.m, paddingVertical: spacing.xl },
  image: { width: 200, height: 200 },
  title: { fontSize: 20, fontWeight: "800", color: colors.text, textAlign: "center" },
  text: { fontSize: 15, color: colors.textMuted, textAlign: "center", lineHeight: 22 },
});
