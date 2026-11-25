import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { useAuth } from "../../src/auth/AuthContext";
import { membershipStatusText } from "../../src/houses";
import { colors, spacing } from "../../src/theme";
import { Avatar } from "../../src/ui/Avatar";
import { Row } from "../../src/ui/Row";
import { Screen } from "../../src/ui/Screen";

export default function ProfileScreen() {
  const { state, signOut } = useAuth();
  if (state.status !== "signedIn") return null;
  const user = state.user;

  async function logout() {
    await signOut();
    router.replace("/welcome");
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Avatar id={user.avatar_id} size={88} />
        <Text style={styles.name} testID="profile-name">{user.display_name}</Text>
        <Text style={styles.muted}>{user.email}</Text>
      </View>
      <Row title="Изменить профиль" subtitle="Имя, аватар, телефон" onPress={() => router.push("/settings/edit")} testID="profile-edit" />
      <Row title="Мой адрес" subtitle={membershipStatusText(user.membership)} onPress={() => router.push("/settings/address")} testID="profile-address" />
      <Row title="Мои устройства" subtitle="Где выполнен вход" onPress={() => router.push("/settings/devices")} testID="profile-devices" />
      <Row title="Мои данные" subtitle="Посмотреть и сохранить" onPress={() => router.push("/settings/data")} testID="profile-data" />
      <Row title="Удалить аккаунт" subtitle="Данные будут стёрты" onPress={() => router.push("/settings/delete")} danger testID="profile-delete" />
      <Row title="Выйти" onPress={logout} testID="profile-logout" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: "center", gap: spacing.xs, paddingVertical: spacing.l },
  name: { fontSize: 24, fontWeight: "800", color: colors.text },
  muted: { color: colors.textMuted, fontSize: 15 },
});
