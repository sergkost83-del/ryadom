import { Platform, Share } from "react-native";

interface WebGlobals {
  document?: { createElement(tag: string): { href: string; download: string; click(): void } };
  Blob?: new (parts: string[], options: { type: string }) => unknown;
  URL?: { createObjectURL(blob: unknown): string; revokeObjectURL(url: string): void };
}

/** В вебе скачивает файл, на телефоне открывает системное окно «Поделиться». */
export async function saveText(fileName: string, text: string): Promise<void> {
  if (Platform.OS === "web") {
    const web = globalThis as unknown as WebGlobals;
    if (web.document && web.Blob && web.URL) {
      const url = web.URL.createObjectURL(new web.Blob([text], { type: "application/json" }));
      const link = web.document.createElement("a");
      link.href = url;
      link.download = fileName;
      link.click();
      web.URL.revokeObjectURL(url);
      return;
    }
  }
  await Share.share({ message: text });
}
