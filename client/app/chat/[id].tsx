import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { errorMessage } from "../../src/api/errors";
import { api } from "../../src/api/instance";
import type { ChatMessage } from "../../src/api/types";
import { canSendChat, formatChatTime, sanitizeChatBody } from "../../src/chat";
import { colors, radius, spacing } from "../../src/theme";
import { Avatar } from "../../src/ui/Avatar";
import { Banner } from "../../src/ui/Banner";
import { Button } from "../../src/ui/Button";
import { Screen } from "../../src/ui/Screen";

export default function ChatRoomScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const roomId = String(id ?? "");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMessages((await api.chatMessages(roomId)).messages);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [roomId]);

  useEffect(() => {
    if (roomId) void load();
  }, [roomId, load]);

  async function send() {
    if (!canSendChat(draft) || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.sendChatMessage(roomId, sanitizeChatBody(draft));
      setDraft("");
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function run(action: () => Promise<unknown>, done: string) {
    setError(null);
    setInfo(null);
    try {
      await action();
      setInfo(done);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <Screen scroll={false} padded={false}>
      <ScrollView style={styles.list} contentContainerStyle={styles.listContent}>
        {error ? <Banner message={error} testID="chat-error" /> : null}
        {info ? <Banner kind="info" message={info} testID="chat-info" /> : null}
        {messages.map((message) => (
          <View key={message.id} style={[styles.bubble, message.mine ? styles.mine : styles.theirs]} testID="chat-message">
            {!message.mine && message.author ? (
              <View style={styles.authorRow}>
                <Avatar id={message.author.avatar_id} size={24} />
                <Text style={styles.author}>{message.author.display_name}</Text>
              </View>
            ) : null}
            {/* Текст выводится как обычный текст: HTML и скрипты не исполняются */}
            <Text style={styles.body}>{message.body}</Text>
            <Text style={styles.time}>{formatChatTime(message.created_at)}</Text>
            <View style={styles.actions}>
              {message.mine ? (
                <Button title="Удалить" variant="link" onPress={() => run(() => api.deleteChatMessage(message.id), "Сообщение удалено.")} testID="chat-delete" />
              ) : (
                <>
                  <Button title="Пожаловаться" variant="link" onPress={() => run(() => api.reportChatMessage(message.id, "Нарушение правил"), "Жалоба отправлена модератору.")} testID="chat-report" />
                  {message.author ? <Button title="Заблокировать автора" variant="link" onPress={() => run(() => api.blockChatAuthor(message.id), "Автор скрыт для вас.")} testID="chat-block" /> : null}
                </>
              )}
            </View>
          </View>
        ))}
        {messages.length === 0 && !error ? <Text style={styles.muted}>Сообщений пока нет. Напишите первым.</Text> : null}
      </ScrollView>
      <View style={styles.composer}>
        <TextInput
          testID="chat-input"
          value={draft}
          onChangeText={setDraft}
          placeholder="Сообщение"
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={1000}
          style={styles.input}
        />
        <Button title="Отправить" onPress={send} disabled={!canSendChat(draft)} loading={busy} testID="chat-send" />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  list: { flex: 1 },
  listContent: { padding: spacing.l, gap: spacing.m },
  bubble: { maxWidth: "85%", borderRadius: radius.l, padding: spacing.m, gap: spacing.xs },
  mine: { alignSelf: "flex-end", backgroundColor: colors.primaryTint },
  theirs: { alignSelf: "flex-start", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  authorRow: { flexDirection: "row", alignItems: "center", gap: spacing.s },
  author: { fontSize: 13, fontWeight: "700", color: colors.textMuted },
  body: { fontSize: 16, lineHeight: 22, color: colors.text },
  time: { fontSize: 12, color: colors.textMuted, alignSelf: "flex-end" },
  actions: { flexDirection: "row", gap: spacing.m, flexWrap: "wrap" },
  muted: { color: colors.textMuted, fontSize: 15, textAlign: "center" },
  composer: { flexDirection: "row", alignItems: "flex-end", gap: spacing.s, padding: spacing.m, borderTopWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  input: { flex: 1, maxHeight: 120, borderWidth: 1, borderColor: colors.border, borderRadius: radius.m, paddingHorizontal: spacing.m, paddingVertical: 10, fontSize: 16, color: colors.text, backgroundColor: colors.background },
});
