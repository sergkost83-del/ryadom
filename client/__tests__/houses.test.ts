import { addressLine, buildingsOf, findBuilding, membershipStatusText, streetsOf } from "../src/houses";
import type { DirectoryCommunity } from "../src/api/types";

const directory: DirectoryCommunity[] = [
  {
    id: "c1", name: "Новые горизонты", slug: "novye-gorizonty", locality: "Бугры",
    streets: [{ id: "s1", name: "Тихая", buildings: [{ id: "b1", label: "1" }, { id: "b2", label: "2 к1" }] }],
  },
  { id: "c2", name: "Стороны света", slug: "storony-sveta", locality: "Бугры", streets: [{ id: "s2", name: "Гаражный проезд", buildings: [{ id: "b3", label: "5" }] }] },
];

describe("справочник адресов", () => {
  it("находит улицы и дома выбранного ЖК", () => {
    expect(streetsOf(directory, "c1").length).toBe(1);
    expect(streetsOf(directory, "нет").length).toBe(0);
    expect(buildingsOf(streetsOf(directory, "c1"), "s1").length).toBe(2);
    expect(buildingsOf([], null).length).toBe(0);
  });
  it("находит дом вместе с улицей и ЖК", () => {
    const found = findBuilding(directory, "b3");
    expect(found?.community.name).toBe("Стороны света");
    expect(found?.street.name).toBe("Гаражный проезд");
    expect(findBuilding(directory, "нет")).toBeNull();
    expect(findBuilding(directory, null)).toBeNull();
  });
  it("формирует строку адреса и статус", () => {
    const info = { id: "b1", label: "1", street: "Тихая", community: { id: "c1", name: "Новые горизонты" } };
    expect(addressLine(info)).toBe("Новые горизонты, Тихая, 1");
    expect(membershipStatusText(null)).toBe("Адрес не указан");
    expect(membershipStatusText({ status: "confirmed", building: info })).toBe("Адрес подтверждён");
    expect(membershipStatusText({ status: "pending", building: info })).toContain("на проверке");
  });
});

import { formatDate } from "../src/format";

describe("даты", () => {
  it("некорректная дата даёт пустую строку", () => {
    expect(formatDate("не дата")).toBe("");
  });
  it("корректная дата даёт непустую строку", () => {
    expect(formatDate("2026-11-05T10:00:00Z").length).toBeGreaterThan(0);
  });
});
