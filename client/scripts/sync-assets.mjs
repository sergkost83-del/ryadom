// Копирует нужные приложению изображения из design/assets в client/assets.
// Запуск: npm run assets (перед start, typecheck и export).
import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "design", "assets");
const target = join(here, "..", "assets");

if (!existsSync(source)) {
  console.error(`Нет папки ${source}. Сначала примените обновление с изображениями.`);
  process.exit(1);
}

function copy(folder, filter, destination) {
  const from = join(source, folder);
  const to = join(target, destination);
  mkdirSync(to, { recursive: true });
  let count = 0;
  for (const name of readdirSync(from)) {
    if (filter(name)) {
      cpSync(join(from, name), join(to, name));
      count += 1;
    }
  }
  return count;
}

const total =
  copy("avatars", () => true, "images/avatars") +
  copy("covers", () => true, "images/covers") +
  copy("illustrations", (n) => n.startsWith("state_") || n.startsWith("empty_"), "images/illustrations") +
  copy("brand", (n) => n === "logo-mark_512.webp", "images/brand") +
  copy(
    "brand",
    (n) => ["app-icon-1024.png", "adaptive-foreground.png", "favicon.png", "splash-icon.png"].includes(n),
    "brand"
  );
console.log(`Скопировано файлов: ${total}`);
