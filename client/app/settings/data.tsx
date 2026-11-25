import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import { saveText } from "../../src/download";
import { colors, radius, spacing } from "../../src/theme";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";

export default function DataScreen() {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setText(JSON.stringify(await api.exportData(), null, 2));
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen>
      <Text style={styles.muted}>Здесь все данные, которые мы храним о вас: профиль, адрес, согласия и устройства.</Text>
      {error ? <Banner message={error} testID="data-error" /> : null}
      {text ? (
        <>
          <Button title="Сохранить файл" onPress={() => saveText("ryadom-my-data.json", text)} testID="data-save" />
          <Text style={styles.json} selectable testID="data-json">{text}</Text>
        </>
      ) : error ? (
        <Button title="Повторить" onPress={load} />
      ) : (
        <Text style={styles.muted}>Загружаем…</Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  muted: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
  json: { fontFamily: "monospace", fontSize: 12, color: colors.text, backgroundColor: colors.fillSoft, borderRadius: radius.m, padding: spacing.m },
});
