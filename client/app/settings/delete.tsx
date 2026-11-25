import { router } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import { useAuth } from "../../src/auth/AuthContext";
import { colors } from "../../src/theme";
import { isValidEmail, normalizeEmail } from "../../src/validation";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";
import { TextField } from "../../src/ui/TextField";

export default function DeleteScreen() {
  const { state, signOut } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (state.status !== "signedIn") return null;
  const matches = isValidEmail(email) && normalizeEmail(email) === state.user.email;

  async function submit() {
    if (!matches || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(normalizeEmail(email));
      await signOut();
      router.replace("/welcome");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Text style={styles.text}>Аккаунт закроется сразу на всех устройствах, а данные будут стёрты через 30 дней. Если за это время вы снова войдёте по коду, удаление отменится.</Text>
      <TextField label="Введите свой e-mail для подтверждения" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="delete-email" />
      {error ? <Banner message={error} testID="delete-error" /> : null}
      <Button title="Удалить аккаунт" onPress={submit} variant="danger" disabled={!matches} loading={busy} testID="delete-submit" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  text: { fontSize: 16, lineHeight: 24, color: colors.text },
});
