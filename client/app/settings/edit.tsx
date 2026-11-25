import { router } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ApiError, errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import { AVATARS_256 } from "../../src/assets";
import { useAuth } from "../../src/auth/AuthContext";
import { colors, spacing } from "../../src/theme";
import { cleanDisplayName, cleanPhone, nameError } from "../../src/validation";
import { Avatar } from "../../src/ui/Avatar";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";
import { TextField } from "../../src/ui/TextField";

export default function EditProfileScreen() {
  const { state, setUser } = useAuth();
  const user = state.status === "signedIn" ? state.user : null;
  const [name, setName] = useState(user?.display_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [avatar, setAvatar] = useState(user?.avatar_id ?? 1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  if (!user) return null;
  const nameProblem = nameError(name);
  const cleanedPhone = cleanPhone(phone);
  const phoneProblem = cleanedPhone === null ? "Телефон: от 10 до 15 цифр, можно с плюсом." : null;

  async function save() {
    if (nameProblem || cleanedPhone === null || busy) return;
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const updated = await api.updateMe({ display_name: cleanDisplayName(name), avatar_id: avatar, phone: cleanedPhone });
      setUser(updated);
      router.back();
    } catch (e) {
      setError(errorMessage(e));
      if (e instanceof ApiError) setFieldErrors(e.fieldErrors);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Text style={styles.label}>Аватар</Text>
      <View style={styles.grid}>
        {AVATARS_256.map((_, index) => (
          <Pressable key={index} testID={`avatar-${index + 1}`} accessibilityRole="button" accessibilityState={{ selected: avatar === index + 1 }} onPress={() => setAvatar(index + 1)} style={[styles.avatar, avatar === index + 1 && styles.avatarSelected]}>
            <Avatar id={index + 1} size={64} />
          </Pressable>
        ))}
      </View>
      <TextField label="Имя" value={name} onChangeText={setName} autoCapitalize="words" error={nameProblem ?? fieldErrors.display_name} testID="edit-name" />
      <TextField label="Телефон (необязательно)" value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+7 900 000-00-00" error={phoneProblem ?? fieldErrors.phone} testID="edit-phone" />
      {error ? <Banner message={error} testID="edit-error" /> : null}
      <Button title="Сохранить" onPress={save} disabled={!!nameProblem || cleanedPhone === null} loading={busy} testID="edit-save" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  label: { color: colors.textMuted, fontSize: 14, fontWeight: "600" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.m },
  avatar: { borderRadius: 40, padding: 3, borderWidth: 3, borderColor: "transparent" },
  avatarSelected: { borderColor: colors.primary },
});
