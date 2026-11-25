import { router } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import { flow } from "../../src/flow";
import { colors } from "../../src/theme";
import { isValidEmail, normalizeEmail } from "../../src/validation";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";
import { TextField } from "../../src/ui/TextField";

export default function EmailScreen() {
  const [email, setEmail] = useState(flow.email);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const valid = isValidEmail(email);

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      const normalized = normalizeEmail(email);
      await api.requestCode(normalized);
      flow.email = normalized;
      router.push("/code");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Text style={styles.title}>Ваш e-mail</Text>
      <Text style={styles.text}>Мы отправим на него код для входа. Пароль не нужен.</Text>
      <TextField label="E-mail" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" placeholder="name@example.ru" testID="email-input" />
      {error ? <Banner message={error} testID="email-error" /> : null}
      <Button title="Получить код" onPress={submit} disabled={!valid} loading={busy} testID="email-submit" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 28, fontWeight: "800", color: colors.text },
  text: { fontSize: 16, color: colors.textMuted, lineHeight: 23 },
});
