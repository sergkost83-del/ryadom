import { router } from "expo-router";
import { Image, StyleSheet, Text, View } from "react-native";

import { COVER_GENERIC, LOGO } from "../../src/assets";
import { colors, spacing } from "../../src/theme";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";

export default function Welcome() {
  return (
    <Screen padded={false}>
      <Image source={COVER_GENERIC} style={styles.cover} resizeMode="cover" accessibilityLabel="Жилой комплекс" />
      <View style={styles.body}>
        <View style={styles.brand}>
          <Image source={LOGO} style={styles.logo} accessibilityLabel="Знак РЯДОМ" />
          <Text style={styles.title}>РЯДОМ</Text>
        </View>
        <Text style={styles.subtitle}>Наш дом. Наши соседи. Больше, чем район.</Text>
        <Button title="Продолжить по e-mail" onPress={() => router.push("/email")} testID="welcome-start" />
        <Text style={styles.note}>Регистрация доступна с 18 лет.</Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  cover: { width: "100%", height: 230 },
  body: { padding: spacing.xl, gap: spacing.l },
  brand: { flexDirection: "row", alignItems: "center", gap: spacing.m },
  logo: { width: 56, height: 56 },
  title: { fontSize: 40, fontWeight: "900", color: colors.primary, letterSpacing: 1 },
  subtitle: { fontSize: 17, color: colors.text, lineHeight: 24 },
  note: { fontSize: 13, color: colors.textMuted, textAlign: "center" },
});
