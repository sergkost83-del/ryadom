import { useLocalSearchParams } from "expo-router";
import { StyleSheet, Text } from "react-native";

import { LEGAL_DRAFT_NOTICE, LEGAL_DRAFT_TEXT, LEGAL_TITLES } from "../../src/legal";
import { colors } from "../../src/theme";
import { Banner } from "../../src/ui/Banner";
import { Screen } from "../../src/ui/Screen";

export default function LegalScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const paragraphs = type ? LEGAL_DRAFT_TEXT[type] : undefined;
  if (!type || !paragraphs) {
    return (
      <Screen>
        <Text style={styles.title}>Документ не найден</Text>
      </Screen>
    );
  }
  return (
    <Screen>
      <Text style={styles.title}>{LEGAL_TITLES[type]}</Text>
      <Banner kind="info" message={LEGAL_DRAFT_NOTICE} />
      {paragraphs.map((text) => (
        <Text key={text} style={styles.text}>
          {text}
        </Text>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 24, fontWeight: "800", color: colors.text },
  text: { fontSize: 16, lineHeight: 24, color: colors.text },
});
