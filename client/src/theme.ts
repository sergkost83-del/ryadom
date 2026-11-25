// Цвета и размеры взяты из прототипа (design/tokens.json).
export const colors = {
  primary: "#FF5B45",
  primaryTint: "#FFF0EB",
  background: "#FFFAF7",
  surface: "#FFFFFF",
  text: "#11192C",
  textMuted: "#68758D",
  border: "#DCE2E8",
  fillSoft: "#EDF0F4",
  infoTint: "#EEF5FF",
  danger: "#B3261E",
  success: "#1B7F4B",
} as const;

export const radius = { s: 14, m: 16, l: 18, xl: 22 } as const;
export const spacing = { xs: 4, s: 8, m: 12, l: 16, xl: 24, xxl: 32 } as const;
