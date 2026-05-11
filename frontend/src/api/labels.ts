/**
 * Русские подписи для enum-значений из форм и из backend-структур.
 * Используется на экране специалиста для отображения извлечённых данных.
 */

const SEX: Record<string, string> = {
  male: "Мужской",
  female: "Женский",
  м: "Мужской",
  ж: "Женский",
};

const ROUTE: Record<string, string> = {
  oral: "Внутрь",
  iv: "Внутривенно",
  im: "Внутримышечно",
  sc: "Подкожно",
  topical: "Местно",
  rectal: "Ректально",
  vaginal: "Вагинально",
  inhalation: "Ингаляционно",
};

const SEVERITY: Record<string, string> = {
  mild: "Лёгкая",
  moderate: "Средняя",
  severe: "Тяжёлая",
  "life-threatening": "Жизнеугрожающая",
  life_threatening: "Жизнеугрожающая",
};

const OUTCOME: Record<string, string> = {
  recovered: "Выздоровление",
  improving: "Улучшение",
  unchanged: "Без изменений",
  worsening: "Ухудшение",
  death: "Смерть",
  unknown: "Неизвестно",
};

const ACTION_TAKEN: Record<string, string> = {
  discontinuation: "Отмена препарата",
  doseReduction: "Снижение дозы",
  treatment: "Назначение лечения",
  hospitalization: "Госпитализация",
  other: "Другие меры",
};

const CAUSALITY_FORM: Record<string, string> = {
  certain: "Определённая",
  probable: "Вероятная",
  possible: "Возможная",
  doubtful: "Сомнительная",
  absent: "Отсутствует",
};

const NARANJO_VERDICT: Record<string, string> = {
  definite: "Определённая",
  probable: "Вероятная",
  possible: "Возможная",
  doubtful: "Сомнительная",
  unclassified: "Неклассифицируемая",
};

const EXPECTEDNESS: Record<string, string> = {
  expected: "Предвиденная",
  unexpected: "Непредвиденная",
  unknown: "Неизвестно",
};

const YES_NO_UNKNOWN: Record<string, string> = {
  yes: "Да",
  no: "Нет",
  unknown: "Неизвестно",
  true: "Да",
  false: "Нет",
};

const DOSAGE_FORM: Record<string, string> = {
  tablets: "Таблетки",
  capsules: "Капсулы",
  injection: "Раствор для инъекций",
  ointment: "Мазь",
  cream: "Крем",
  syrup: "Сироп",
  suspension: "Суспензия",
  drops: "Капли",
  spray: "Спрей",
  other: "Другое",
};

/**
 * Нормализует значение: если бэкенд вернул Python-style repr энума
 * ("SeverityLevel.MILD"), берём часть после точки и приводим к lower-case.
 */
function normalize(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  const afterDot = s.includes(".") ? s.split(".").pop()! : s;
  return afterDot.trim().toLowerCase();
}

function lookup(map: Record<string, string>, value: unknown): string {
  const norm = normalize(value);
  if (!norm) return "";
  return map[norm] ?? String(value);
}

export const labels = {
  sex: (v: unknown) => lookup(SEX, v),
  route: (v: unknown) => lookup(ROUTE, v),
  severity: (v: unknown) => lookup(SEVERITY, v),
  outcome: (v: unknown) => lookup(OUTCOME, v),
  actionTaken: (v: unknown) => lookup(ACTION_TAKEN, v),
  causalityForm: (v: unknown) => lookup(CAUSALITY_FORM, v),
  naranjoVerdict: (v: unknown) => lookup(NARANJO_VERDICT, v),
  expectedness: (v: unknown) => lookup(EXPECTEDNESS, v),
  yesNo: (v: unknown) => lookup(YES_NO_UNKNOWN, v),
  dosageForm: (v: unknown) => lookup(DOSAGE_FORM, v),
};

/**
 * actionTaken может прийти как строка "doseReduction" или как массив
 * ["discontinuation", "doseReduction"]. Возвращает строку через запятую.
 */
export function formatActionTaken(value: unknown): string {
  if (!value) return "";
  if (Array.isArray(value)) {
    return value.map((v) => labels.actionTaken(v)).filter(Boolean).join(", ");
  }
  // Иногда приходит строка через запятую
  if (typeof value === "string" && value.includes(",")) {
    return value
      .split(",")
      .map((v) => labels.actionTaken(v.trim()))
      .filter(Boolean)
      .join(", ");
  }
  return labels.actionTaken(value);
}
