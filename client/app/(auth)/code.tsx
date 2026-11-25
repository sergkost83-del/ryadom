import { router } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api, DEVICE_NAME } from "../../src/api/instance";
import { useAuth } from "../../src/auth/AuthContext";
import { flow } from "../../src/flow";
import { colors } from "../../src/theme";
import { formatCountdown, isValidCode, normalizeCode } from "../../src/validation";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";
import { TextField } from "../../src/ui/TextField";

const RESEND_SECONDS = 60;

export default function CodeScreen() {
  const { signIn } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [seconds, setSeconds] = useState(RESEND_SECONDS);

  useEffect(() => {
    if (!flow.email) router.replace("/email");
  }, []);

  useEffect(() => {
    if (seconds <= 0) return;
    const timer = setTimeout(() => setSeconds((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [seconds]);

  async function submit(value: string) {
    if (!isValidCode(value) || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.verifyCode(flow.email, value, DEVICE_NAME);
      if (result.is_new) {
        flow.registrationToken = result.registration_token;
        router.replace("/register");
      } else {
        await signIn(result.tokens, result.user);
        flow.reset();
        router.replace("/home");
      }
    } catch (e) {
      setError(errorMessage(e));
      setCode("");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await api.requestCode(flow.email);
      setSeconds(RESEND_SECONDS);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <Screen>
      <Text style={styles.title}>Код из письма</Text>
      <Text style={styles.text}>Мы отправили 6 цифр на {flow.email}. Код действует 10 минут.</Text>
      <TextField
        label="Код"
        value={code}
        large
        onChangeText={(text) => {
          const next = normalizeCode(text);
          setCode(next);
          if (isValidCode(next)) void submit(next);
        }}
        keyboardType="number-pad"
        maxLength={6}
        placeholder="000000"
        testID="code-input"
      />
      {error ? <Banner message={error} testID="code-error" /> : null}
      <Button title="Войти" onPress={() => submit(code)} disabled={!isValidCode(code)} loading={busy} testID="code-submit" />
      <Button
        title={seconds > 0 ? `Отправить ещё раз через ${formatCountdown(seconds)}` : "Отправить код ещё раз"}
        onPress={resend}
        variant="link"
        disabled={seconds > 0}
        testID="code-resend"
      />
      <Button title="Изменить e-mail" onPress={() => router.back()} variant="link" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 28, fontWeight: "800", color: colors.text },
  text: { fontSize: 16, color: colors.textMuted, lineHeight: 23 },
});
