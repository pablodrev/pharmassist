import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  ArrowLeft,
  CheckCircle2,
  Edit3,
  Loader2,
  AlertTriangle,
  Send,
  Archive,
} from "lucide-react";
import { toast } from "sonner";
import { labels, formatActionTaken } from "../api/labels";

// ── Types ──────────────────────────────────────────────────────────────────

type ReportResponse = components["schemas"]["ReportResponse"];
type ReportStatus = components["schemas"]["ReportStatus"];

interface Props {
  reportId: string;
  onBack: () => void;
  onFinalized: () => void;
}

type RecType = "completeness" | "ime" | "naranjo" | "expectedness";
type ExtractedSection = "patient" | "reporter" | "drug" | "reaction";

interface Override {
  verdict: "accepted" | "edited";
  comment: string;
}

interface SelectOption {
  value: string;
  label: string;
}

interface SectionFieldDef {
  key: string;
  label: string;
  format?: (v: unknown) => string;
  multiline?: boolean;
  options?: SelectOption[];
}

interface ExtractedSectionState {
  editing: boolean;
  accepted: boolean;
  edits: Record<string, string>;
}

interface NaranjoQuestionEdit {
  answer: string;
  rationale: string;
}

// ── Constants ──────────────────────────────────────────────────────────────

const REC_LABELS: Record<RecType, string> = {
  completeness: "Полнота информации",
  ime: "Клиническая значимость (IME)",
  naranjo: "Причинно-следственная связь (Наранжо)",
  expectedness: "Предвиденность (ИМП)",
};

// Must match backend CaseExtraction.missing_mandatory_fields() strings exactly
const SECTION_COMPLETENESS_LABEL: Record<ExtractedSection, string> = {
  patient: "Информация о пациенте",
  reporter: "Информация о репортёре",
  reaction: "Описание нежелательной реакции",
  drug: "Информация о подозреваемом препарате",
};

const SEX_OPTIONS: SelectOption[] = [
  { value: "Мужской", label: "Мужской" },
  { value: "Женский", label: "Женский" },
];

const ROUTE_OPTIONS: SelectOption[] = [
  { value: "Внутрь", label: "Внутрь" },
  { value: "Внутривенно", label: "Внутривенно" },
  { value: "Внутримышечно", label: "Внутримышечно" },
  { value: "Подкожно", label: "Подкожно" },
  { value: "Местно", label: "Местно" },
  { value: "Ректально", label: "Ректально" },
  { value: "Вагинально", label: "Вагинально" },
  { value: "Ингаляционно", label: "Ингаляционно" },
];

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: "Лёгкая", label: "Лёгкая" },
  { value: "Средняя", label: "Средняя" },
  { value: "Тяжёлая", label: "Тяжёлая" },
  { value: "Жизнеугрожающая", label: "Жизнеугрожающая" },
];

const OUTCOME_OPTIONS: SelectOption[] = [
  { value: "Выздоровление", label: "Выздоровление" },
  { value: "Улучшение", label: "Улучшение" },
  { value: "Без изменений", label: "Без изменений" },
  { value: "Ухудшение", label: "Ухудшение" },
  { value: "Смерть", label: "Смерть" },
  { value: "Неизвестно", label: "Неизвестно" },
];

const YES_NO_OPTIONS: SelectOption[] = [
  { value: "Да", label: "Да" },
  { value: "Нет", label: "Нет" },
  { value: "Неизвестно", label: "Неизвестно" },
];

const SECTION_FIELDS: Record<ExtractedSection, SectionFieldDef[]> = {
  patient: [
    { key: "name", label: "ФИО" },
    { key: "age", label: "Возраст" },
    { key: "sex", label: "Пол", format: labels.sex, options: SEX_OPTIONS },
    { key: "weight", label: "Вес" },
    { key: "diagnosis", label: "Основной диагноз", multiline: true },
    { key: "comorbidities", label: "Сопутствующие заболевания", multiline: true },
  ],
  reporter: [
    { key: "type", label: "Тип репортёра" },
    { key: "name", label: "Имя репортёра" },
    { key: "organization", label: "Организация" },
  ],
  drug: [
    { key: "name", label: "Название препарата" },
    { key: "dose", label: "Доза" },
    { key: "route", label: "Путь введения", format: labels.route, options: ROUTE_OPTIONS },
    { key: "indication", label: "Показание к применению", multiline: true },
    { key: "action_taken", label: "Действия с препаратом", format: formatActionTaken },
    { key: "start_date", label: "Дата начала" },
    { key: "end_date", label: "Дата окончания" },
  ],
  reaction: [
    { key: "description", label: "Описание реакции", multiline: true },
    { key: "severity", label: "Тяжесть", format: labels.severity, options: SEVERITY_OPTIONS },
    { key: "outcome", label: "Исход", format: labels.outcome, options: OUTCOME_OPTIONS },
    { key: "is_serious", label: "Серьёзная НР", format: labels.yesNo, options: YES_NO_OPTIONS },
    { key: "onset_date", label: "Дата начала реакции" },
    { key: "seriousness_criteria", label: "Критерии серьёзности" },
  ],
};

const NARANJO_ANSWER_LABELS: Record<string, string> = {
  yes: "Да",
  no: "Нет",
  unknown: "Неизвестно",
};

const NARANJO_VERDICT_OPTIONS = [
  "Определённая",
  "Вероятная",
  "Возможная",
  "Сомнительная",
  "Условная/Неклассифицируемая",
  "Неоцениваемая",
];

function getSectionData(data: Record<string, unknown> | undefined | null, section: ExtractedSection): Record<string, unknown> {
  if (!data) return {};
  switch (section) {
    case "patient": return (data.patient as Record<string, unknown>) ?? {};
    case "reporter": return (data.reporter as Record<string, unknown>) ?? {};
    case "drug": return (data.suspect_drug as Record<string, unknown>) ?? {};
    case "reaction": return (data.adverse_reaction as Record<string, unknown>) ?? {};
  }
}

const INIT_SECTION: ExtractedSectionState = { editing: false, accepted: false, edits: {} };

// ── Main Component ─────────────────────────────────────────────────────────

export function SpecialistReviewPage({ reportId, onBack, onFinalized }: Props) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  // AI rec section overrides
  const [overrides, setOverrides] = useState<Partial<Record<RecType, Override>>>({});
  const [editing, setEditing] = useState<Partial<Record<RecType, boolean>>>({});

  // Extracted data section states
  const [extractedStates, setExtractedStates] = useState<Record<ExtractedSection, ExtractedSectionState>>({
    patient: { ...INIT_SECTION },
    reporter: { ...INIT_SECTION },
    drug: { ...INIT_SECTION },
    reaction: { ...INIT_SECTION },
  });

  // Naranjo question edits
  const [naranjoEdits, setNaranjoEdits] = useState<Record<number, NaranjoQuestionEdit>>({});
  const [naranjoVerdictEdit, setNaranjoVerdictEdit] = useState("");

  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [returning, setReturning] = useState(false);
  const [returnComment, setReturnComment] = useState("");
  const [showReturnModal, setShowReturnModal] = useState(false);

  // ── Load ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const load = async () => {
      const { data, error } = await apiClient.GET("/api/v1/reports/{report_id}", {
        params: { path: { report_id: reportId } },
      });
      if (cancelled) return;
      if (error || !data) { toast.error("Не удалось загрузить отчёт"); setLoading(false); return; }
      if (data.status === "submitted") {
        await apiClient.PATCH("/api/v1/reports/{report_id}/status", {
          params: { path: { report_id: reportId } },
          body: { status: "analysis" },
        });
      }
      setReport(data);
      setLoading(false);
      if (data.ai_recommendations.analysis_status !== "ready") setPolling(true);
    };
    load();
    return () => { cancelled = true; };
  }, [reportId]);

  // ── Poll ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!polling) return;
    let cancelled = false;
    const tick = async () => {
      const { data } = await apiClient.GET("/api/v1/reports/{report_id}/analysis-status", {
        params: { path: { report_id: reportId } },
      });
      if (cancelled) return;
      if (data?.analysis_status === "ready") {
        const { data: full } = await apiClient.GET("/api/v1/reports/{report_id}", {
          params: { path: { report_id: reportId } },
        });
        if (!cancelled && full) { setReport(full); setPolling(false); }
      } else if (data?.analysis_status === "failed") {
        toast.error("AI-анализ завершился ошибкой: " + (data.error ?? ""));
        setPolling(false);
      } else {
        setTimeout(tick, 3000);
      }
    };
    const handle = setTimeout(tick, 3000);
    return () => { cancelled = true; clearTimeout(handle); };
  }, [polling, reportId]);

  const recs = report?.ai_recommendations;

  const allCaptured = useMemo(() => {
    if (!recs) return false;
    return (["completeness", "ime", "naranjo", "expectedness"] as RecType[]).every((t) => {
      if (!recs[t]) return true;
      return Boolean(overrides[t]);
    });
  }, [recs, overrides]);

  // ── AI rec handlers ───────────────────────────────────────────────────────
  const handleAccept = (type: RecType) => {
    setOverrides((o) => {
      const next = { ...o };
      if (next[type]?.verdict === "accepted") {
        delete next[type];
      } else {
        let comment = next[type]?.comment ?? "";
        if (type === "naranjo" && Object.keys(naranjoEdits).length > 0) {
          comment = JSON.stringify({
            question_edits: naranjoEdits,
            ...(naranjoVerdictEdit ? { verdict_override: naranjoVerdictEdit } : {}),
          });
        }
        next[type] = { verdict: "accepted", comment };
      }
      return next;
    });
    setEditing((e) => ({ ...e, [type]: false }));
  };

  const handleStartEdit = (type: RecType) => {
    if (editing[type]) {
      setEditing((e) => ({ ...e, [type]: false }));
      setOverrides((o) => {
        if (o[type]?.verdict !== "edited") return o;
        const next = { ...o }; delete next[type]; return next;
      });
      return;
    }
    setEditing((e) => ({ ...e, [type]: true }));
    if (!overrides[type]) setOverrides((o) => ({ ...o, [type]: { verdict: "edited", comment: "" } }));
  };

  const handleCommentChange = (type: RecType, comment: string) =>
    setOverrides((o) => ({ ...o, [type]: { verdict: "edited", comment } }));

  // ── Extracted section handlers ────────────────────────────────────────────
  const handleExtractedAccept = (section: ExtractedSection) =>
    setExtractedStates((s) => ({
      ...s,
      [section]: { ...s[section], accepted: !s[section].accepted, editing: false },
    }));

  const handleExtractedEdit = (section: ExtractedSection) =>
    setExtractedStates((s) => ({
      ...s,
      [section]: { ...s[section], editing: !s[section].editing },
    }));

  const handleExtractedFieldChange = (section: ExtractedSection, key: string, value: string) =>
    setExtractedStates((s) => ({
      ...s,
      [section]: { ...s[section], edits: { ...s[section].edits, [key]: value } },
    }));

  // ── Naranjo handlers ──────────────────────────────────────────────────────
  const handleNaranjoAnswer = (qId: number, answer: string) =>
    setNaranjoEdits((e) => ({ ...e, [qId]: { answer, rationale: e[qId]?.rationale ?? "" } }));

  const handleNaranjoRationale = (qId: number, rationale: string) =>
    setNaranjoEdits((e) => ({ ...e, [qId]: { answer: e[qId]?.answer ?? "unknown", rationale } }));

  // ── Save / finalize / return ──────────────────────────────────────────────
  const handleSaveOverrides = async () => {
    setSaving(true);
    try {
      const { error } = await apiClient.PATCH("/api/v1/reports/{report_id}/specialist-review", {
        params: { path: { report_id: reportId } },
        body: {
          completeness: overrides.completeness ?? null,
          ime: overrides.ime ?? null,
          naranjo: overrides.naranjo ?? null,
          expectedness: overrides.expectedness ?? null,
        } as components["schemas"]["SpecialistReviewRequest"],
      });
      if (error) throw new Error("Не удалось сохранить правки");
      toast.success("Правки сохранены");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  const handleFinalize = async () => {
    if (!allCaptured) { toast.error("Сначала примите или отредактируйте все рекомендации"); return; }
    setFinalizing(true);
    try {
      await handleSaveOverrides();
      const { error } = await apiClient.POST("/api/v1/reports/{report_id}/finalize", {
        params: { path: { report_id: reportId } },
      });
      if (error) throw new Error("Не удалось финализировать");
      toast.success("Отчёт финализирован");
      onFinalized();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка финализации");
    } finally {
      setFinalizing(false);
    }
  };

  const handleReturnForRevision = async () => {
    if (!returnComment.trim()) { toast.error("Укажите причину возврата"); return; }
    setReturning(true);
    try {
      const { error } = await apiClient.PATCH("/api/v1/reports/{report_id}/status", {
        params: { path: { report_id: reportId } },
        body: { status: "clarification", comment: returnComment.trim() },
      });
      if (error) throw new Error("Не удалось вернуть отчёт");
      toast.success("Отчёт возвращён медработнику");
      setShowReturnModal(false);
      onFinalized();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка возврата");
    } finally {
      setReturning(false);
    }
  };

  const missingFieldsFromAI = useMemo(() => {
    const c = recs?.completeness as { missing_mandatory_fields?: string[]; warnings?: string[] } | undefined | null;
    if (!c) return "";
    const lines: string[] = [];
    if (c.missing_mandatory_fields?.length)
      lines.push("Не хватает данных: " + c.missing_mandatory_fields.join(", "));
    if (c.warnings?.length)
      lines.push(...c.warnings.filter((w: string) => !w.startsWith("Ошибка оценки")));
    return lines.join("\n");
  }, [recs]);

  // ── Render ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        <Loader2 className="w-5 h-5 mr-2 animate-spin" /> Загрузка отчёта...
      </div>
    );
  }
  if (!report) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <p className="text-gray-600 mb-4">Отчёт не найден</p>
        <Button onClick={onBack}>Назад к очереди</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 bg-gradient_main">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="mb-4">
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Вернуться к очереди
          </Button>
        </div>

        {/* Header */}
        <Card className="p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold mb-1">
                {report.drug?.name_ru ?? "Препарат не определён"}
              </h2>
              <p className="text-sm text-gray-500">
                #{report.id.slice(0, 8)} • {new Date(report.created_at).toLocaleString("ru-RU")}
              </p>
            </div>
            <Badge variant="outline">{statusLabel(report.status)}</Badge>
          </div>
          <div className="bg-gray-50 rounded p-4">
            <p className="text-sm text-gray-600 mb-1 font-medium">Исходный текст сообщения:</p>
            <p className="text-sm whitespace-pre-wrap">{report.raw_text}</p>
          </div>
        </Card>

        {/* Editable extracted sections */}
        {report.extracted_data && (
          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Извлечённые данные
            </p>
            <div className="space-y-3">
              {(["patient", "reporter", "drug", "reaction"] as ExtractedSection[]).map((sec) => (
                <EditableSectionCard
                  key={sec}
                  section={sec}
                  data={getSectionData(report.extracted_data as Record<string, unknown>, sec)}
                  state={extractedStates[sec]}
                  onAccept={() => handleExtractedAccept(sec)}
                  onEdit={() => handleExtractedEdit(sec)}
                  onFieldChange={(key, val) => handleExtractedFieldChange(sec, key, val)}
                />
              ))}
            </div>
          </div>
        )}

        {/* AI banner */}
        {recs?.analysis_status !== "ready" && (
          <Card className="p-4 mb-6 bg-blue-50 border-blue-200">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              <div>
                <p className="font-medium text-blue-900">AI ещё анализирует</p>
                <p className="text-sm text-blue-700">
                  Рекомендации появятся через несколько секунд. Статус обновляется автоматически.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* AI recs */}
        {recs?.analysis_status === "ready" && (
          <div className="space-y-4">
            {(["completeness", "ime", "naranjo", "expectedness"] as RecType[])
              .filter((t) => recs[t])
              .map((type) => (
                <RecommendationCard
                  key={type}
                  type={type}
                  data={recs[type] as Record<string, unknown>}
                  override={overrides[type]}
                  isEditing={!!editing[type]}
                  onAccept={() => handleAccept(type)}
                  onEdit={() => handleStartEdit(type)}
                  onCommentChange={(c) => handleCommentChange(type, c)}
                  naranjoEdits={naranjoEdits}
                  naranjoVerdictEdit={naranjoVerdictEdit}
                  onNaranjoAnswer={handleNaranjoAnswer}
                  onNaranjoRationale={handleNaranjoRationale}
                  onNaranjoVerdict={setNaranjoVerdictEdit}
                />
              ))}

            <div className="flex flex-wrap gap-3 justify-end pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => { setReturnComment(missingFieldsFromAI); setShowReturnModal(true); }}
                disabled={report.status === "finalized" || report.status === "clarification"}
              >
                <Send className="w-4 h-4 mr-2" /> Вернуть на доработку
              </Button>
              <Button variant="outline" onClick={handleSaveOverrides} disabled={saving}>
                {saving ? "Сохранение..." : "Сохранить правки"}
              </Button>
              <Button
                onClick={handleFinalize}
                disabled={!allCaptured || finalizing || report.status === "finalized"}
              >
                <Archive className="w-4 h-4 mr-2" />
                {finalizing ? "Финализация..." : "Финализировать"}
              </Button>
            </div>
            {!allCaptured && (
              <p className="text-xs text-gray-500 text-right">
                Чтобы финализировать, примите или отредактируйте каждую рекомендацию.
              </p>
            )}
          </div>
        )}

        {/* Return modal */}
        {showReturnModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-lg p-6">
              <h3 className="font-semibold mb-3">Возврат на доработку</h3>
              <p className="text-sm text-gray-600 mb-3">
                Комментарий будет виден медработнику.
              </p>
              <Textarea
                value={returnComment}
                onChange={(e) => setReturnComment(e.target.value)}
                rows={6}
                placeholder="Опишите, что нужно дополнить..."
              />
              <div className="flex justify-end gap-2 mt-4">
                <Button variant="outline" onClick={() => setShowReturnModal(false)} disabled={returning}>
                  Отмена
                </Button>
                <Button onClick={handleReturnForRevision} disabled={returning}>
                  {returning ? "Отправка..." : "Отправить"}
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

// ── EditableSectionCard ────────────────────────────────────────────────────

function EditableSectionCard({
  section,
  data,
  state,
  onAccept,
  onEdit,
  onFieldChange,
}: {
  section: ExtractedSection;
  data: Record<string, unknown>;
  state: ExtractedSectionState;
  onAccept: () => void;
  onEdit: () => void;
  onFieldChange: (key: string, value: string) => void;
}) {
  const fields = SECTION_FIELDS[section];
  const label = SECTION_COMPLETENESS_LABEL[section];
  const hasAnyData = fields.some((f) => {
    const v = data[f.key];
    return v !== null && v !== undefined && String(v).trim() !== "";
  });

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h4 className="font-medium text-sm">{label}</h4>
          {state.accepted && (
            <Badge className="bg-green-100 text-green-800" variant="outline">
              <CheckCircle2 className="w-3 h-3 mr-1" /> Принято
            </Badge>
          )}
          {!hasAnyData && (
            <Badge className="bg-yellow-100 text-yellow-800" variant="outline">
              Нет данных
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant={state.accepted ? "default" : "outline"} onClick={onAccept}>
            <CheckCircle2 className="w-3 h-3 mr-1" /> Принять
          </Button>
          <Button size="sm" variant={state.editing ? "default" : "outline"} onClick={onEdit}>
            <Edit3 className="w-3 h-3 mr-1" /> Редактировать
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {fields.map((field) => {
          const raw = data[field.key];
          const editVal = state.edits[field.key];
          const rawStr = raw !== null && raw !== undefined ? String(raw) : "";
          // For select fields, initialise from the formatted raw value so it matches option labels
          const formattedRaw = raw !== null && raw !== undefined
            ? (field.format ? field.format(raw) || rawStr : rawStr)
            : "";
          const selectVal = editVal !== undefined ? editVal : formattedRaw;
          const currentVal = editVal !== undefined ? editVal : rawStr;
          const displayVal = editVal !== undefined && editVal !== ""
            ? editVal
            : formattedRaw;

          if (state.editing) {
            return (
              <div key={field.key} className="grid grid-cols-3 gap-2 items-start">
                <label className="text-xs text-gray-500 pt-2">{field.label}</label>
                {field.options ? (
                  <Select
                    value={selectVal}
                    onValueChange={(v) => onFieldChange(field.key, v)}
                  >
                    <SelectTrigger className="col-span-2 text-sm">
                      <SelectValue placeholder="Выберите значение" />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : field.multiline ? (
                  <Textarea
                    className="col-span-2 text-sm"
                    value={currentVal}
                    onChange={(e) => onFieldChange(field.key, e.target.value)}
                    rows={2}
                    placeholder={field.label}
                  />
                ) : (
                  <Input
                    className="col-span-2 text-sm"
                    value={currentVal}
                    onChange={(e) => onFieldChange(field.key, e.target.value)}
                    placeholder={field.label}
                  />
                )}
              </div>
            );
          }

          if (!displayVal) return null;

          return (
            <div key={field.key} className="grid grid-cols-3 gap-2">
              <span className="text-xs text-gray-500">{field.label}</span>
              <span className="text-sm col-span-2 text-gray-800">
                {displayVal}
                {editVal !== undefined && editVal !== "" && (
                  <span className="ml-1 text-xs text-orange-500">(изменено)</span>
                )}
              </span>
            </div>
          );
        })}
        {!hasAnyData && !state.editing && (
          <p className="text-xs text-gray-400 italic">Данные не извлечены</p>
        )}
      </div>
    </Card>
  );
}

// ── RecommendationCard ─────────────────────────────────────────────────────

function RecommendationCard({
  type,
  data,
  override,
  isEditing,
  onAccept,
  onEdit,
  onCommentChange,
  naranjoEdits,
  naranjoVerdictEdit,
  onNaranjoAnswer,
  onNaranjoRationale,
  onNaranjoVerdict,
}: {
  type: RecType;
  data: Record<string, unknown>;
  override?: Override;
  isEditing: boolean;
  onAccept: () => void;
  onEdit: () => void;
  onCommentChange: (c: string) => void;
  naranjoEdits: Record<number, NaranjoQuestionEdit>;
  naranjoVerdictEdit: string;
  onNaranjoAnswer: (qId: number, answer: string) => void;
  onNaranjoRationale: (qId: number, rationale: string) => void;
  onNaranjoVerdict: (v: string) => void;
}) {
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{REC_LABELS[type]}</h3>
          {override?.verdict === "accepted" && (
            <Badge className="bg-green-100 text-green-800" variant="outline">
              <CheckCircle2 className="w-3 h-3 mr-1" /> Принято
            </Badge>
          )}
          {override?.verdict === "edited" && (
            <Badge className="bg-orange-100 text-orange-800" variant="outline">
              <Edit3 className="w-3 h-3 mr-1" /> Отредактировано
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant={override?.verdict === "accepted" ? "default" : "outline"} onClick={onAccept}>
            <CheckCircle2 className="w-4 h-4 mr-1" /> Принять
          </Button>
          <Button size="sm" variant={isEditing ? "default" : "outline"} onClick={onEdit}>
            <Edit3 className="w-4 h-4 mr-1" /> Редактировать
          </Button>
        </div>
      </div>

      <div className="text-sm space-y-2">
        {type === "completeness" && <CompletenessView data={data} />}
        {type === "ime" && <IMEView data={data} />}
        {type === "naranjo" && (
          <NaranjoView
            data={data}
            isEditing={isEditing}
            edits={naranjoEdits}
            verdictEdit={naranjoVerdictEdit}
            onAnswerChange={onNaranjoAnswer}
            onRationaleChange={onNaranjoRationale}
            onVerdictChange={onNaranjoVerdict}
          />
        )}
        {type === "expectedness" && <ExpectednessView data={data} />}
      </div>

      {isEditing && type !== "naranjo" && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-1">Комментарий специалиста:</p>
          <Textarea
            value={override?.comment ?? ""}
            onChange={(e) => onCommentChange(e.target.value)}
            rows={3}
            placeholder="Обоснование правки..."
          />
        </div>
      )}
      {isEditing && type === "naranjo" && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-1">Дополнительный комментарий:</p>
          <Textarea
            value={override?.comment ?? ""}
            onChange={(e) => onCommentChange(e.target.value)}
            rows={2}
            placeholder="Дополнительные замечания к оценке..."
          />
        </div>
      )}
    </Card>
  );
}

// ── CompletenessView ───────────────────────────────────────────────────────

function CompletenessView({ data }: { data: Record<string, unknown> }) {
  const missing = (data.missing_mandatory_fields as string[] | undefined) ?? [];
  const warnings = (data.warnings as string[] | undefined) ?? [];
  const relevantWarnings = warnings.filter((w) => !w.startsWith("Ошибка оценки"));

  const sections: { label: string }[] = [
    { label: "Информация о пациенте" },
    { label: "Информация о репортёре" },
    { label: "Описание нежелательной реакции" },
    { label: "Информация о подозреваемом препарате" },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {sections.map(({ label }) => {
          const absent = missing.includes(label);
          return (
            <div
              key={label}
              className={`flex items-center gap-2 p-2 rounded text-xs font-medium ${
                absent
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-green-50 text-green-700 border border-green-200"
              }`}
            >
              {absent
                ? <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                : <CheckCircle2 className="w-3 h-3 flex-shrink-0" />}
              {label}
            </div>
          );
        })}
      </div>
      {missing.length > 0 && (
        <p className="text-xs text-red-600">
          Рекомендуется вернуть отчёт на доработку — часть обязательных данных отсутствует.
        </p>
      )}
      {relevantWarnings.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700">Предупреждения:</p>
          <ul className="list-disc list-inside text-xs text-gray-600">
            {relevantWarnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── IMEView ────────────────────────────────────────────────────────────────

function IMEView({ data }: { data: Record<string, unknown> }) {
  const significant = data.is_clinically_significant as boolean | undefined;
  const matches = (data.matches as Array<Record<string, unknown>>) ?? [];
  const extracted = (data.extracted_reactions as string[] | undefined) ?? [];
  const notInIme = (data.reactions_not_in_ime as string[] | undefined) ?? [];
  return (
    <div className="space-y-2">
      <p>
        <span className="font-medium">Вердикт:</span>{" "}
        {significant ? (
          <Badge className="bg-red-100 text-red-800" variant="outline">
            <AlertTriangle className="w-3 h-3 mr-1" /> Клинически значимо
          </Badge>
        ) : (
          <Badge className="bg-gray-100" variant="outline">Не значимо</Badge>
        )}
      </p>
      {extracted.length > 0 && (
        <p className="text-gray-600">
          <span className="font-medium">Извлечённые реакции:</span> {extracted.join(", ")}
        </p>
      )}
      {matches.length > 0 && (
        <div>
          <p className="font-medium text-gray-700">Совпадения с EMA IME:</p>
          <ul className="list-disc list-inside text-gray-600">
            {matches.map((m, i) => (
              <li key={i}>
                {String(m.ime_pt_name ?? m.pt_name ?? m.reaction ?? "—")}{" "}
                {(m.similarity_score !== undefined || m.score !== undefined) && (
                  <span className="text-xs text-gray-400">
                    (score: {Number(m.similarity_score ?? m.score).toFixed(2)})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {notInIme.length > 0 && (
        <p className="text-gray-500 text-xs">Реакции, не найденные в IME: {notInIme.join(", ")}</p>
      )}
    </div>
  );
}

// ── NaranjoView ────────────────────────────────────────────────────────────

function NaranjoView({
  data,
  isEditing,
  edits,
  verdictEdit,
  onAnswerChange,
  onRationaleChange,
  onVerdictChange,
}: {
  data: Record<string, unknown>;
  isEditing: boolean;
  edits: Record<number, NaranjoQuestionEdit>;
  verdictEdit: string;
  onAnswerChange: (qId: number, answer: string) => void;
  onRationaleChange: (qId: number, rationale: string) => void;
  onVerdictChange: (v: string) => void;
}) {
  const score = data.total_score as number | undefined;
  const verdict = data.verdict as string | undefined;
  const confidence = data.confidence as string | undefined;
  const missing = (data.missing_data_for_assessment as string[] | undefined) ?? [];
  const questions = (data.questions as Array<Record<string, unknown>>) ?? [];
  const displayVerdict = verdictEdit || verdict || "";

  return (
    <div className="space-y-3">
      {/* Summary row */}
      <div className="flex items-center gap-4 flex-wrap">
        <span><span className="font-medium">Балл:</span> {score ?? "—"}</span>
        <div className="flex items-center gap-2">
          <span className="font-medium">Вердикт:</span>
          {isEditing ? (
            <Select value={displayVerdict} onValueChange={onVerdictChange}>
              <SelectTrigger className="h-7 text-xs w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {NARANJO_VERDICT_OPTIONS.map((v) => (
                  <SelectItem key={v} value={v}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Badge className="bg-blue-100 text-blue-800" variant="outline">
              {labels.naranjoVerdict(displayVerdict) || displayVerdict || "—"}
            </Badge>
          )}
        </div>
        {confidence && <span className="text-xs text-gray-500">(уверенность: {confidence})</span>}
      </div>

      {/* Questions */}
      {questions.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Вопросы алгоритма Наранжо:</p>
          {questions.map((q) => {
            const qId = q.question_id as number;
            const qText = q.question_text as string;
            const origAnswer = String(q.answer ?? "unknown");
            const origRationale = String(q.rationale ?? "");
            const qScore = q.score as number;
            const currAnswer = edits[qId]?.answer ?? origAnswer;
            const currRationale = edits[qId]?.rationale ?? origRationale;
            const wasEdited = edits[qId] !== undefined;

            return (
              <div
                key={qId}
                className={`border rounded p-3 ${wasEdited ? "border-orange-200 bg-orange-50" : "border-gray-100 bg-gray-50"}`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-xs text-gray-700 font-medium flex-1">
                    {qId}. {qText}
                  </p>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {isEditing ? (
                      <Select value={currAnswer} onValueChange={(v) => onAnswerChange(qId, v)}>
                        <SelectTrigger className="h-6 text-xs w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="yes">Да</SelectItem>
                          <SelectItem value="no">Нет</SelectItem>
                          <SelectItem value="unknown">Неизвестно</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Badge
                        className={
                          currAnswer === "yes"
                            ? "bg-green-100 text-green-800"
                            : currAnswer === "no"
                              ? "bg-red-100 text-red-800"
                              : "bg-gray-100 text-gray-600"
                        }
                        variant="outline"
                      >
                        {NARANJO_ANSWER_LABELS[currAnswer] ?? currAnswer}
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-xs text-gray-500 w-8 text-center">
                      {qScore > 0 ? `+${qScore}` : qScore}
                    </Badge>
                  </div>
                </div>
                {isEditing ? (
                  <Textarea
                    className="text-xs mt-1"
                    value={currRationale}
                    onChange={(e) => onRationaleChange(qId, e.target.value)}
                    rows={2}
                    placeholder="Обоснование..."
                  />
                ) : (
                  currRationale && (
                    <p className="text-xs text-gray-600 mt-1 italic">{currRationale}</p>
                  )
                )}
              </div>
            );
          })}
        </div>
      )}

      {missing.length > 0 && (
        <p className="text-gray-500 text-xs">Не хватает данных: {missing.join(", ")}</p>
      )}
    </div>
  );
}

// ── ExpectednessView ───────────────────────────────────────────────────────

function ExpectednessView({ data }: { data: Record<string, unknown> }) {
  const verdict = data.verdict as string | undefined;
  const rationale = data.rationale as string | undefined;
  const sections = (data.relevant_smp_sections as string[] | undefined) ?? [];
  const ragUsed = data.rag_used as boolean | undefined;

  const verdictColor = verdict?.includes("Предвиден") || verdict === "expected"
    ? "bg-yellow-100 text-yellow-800"
    : verdict?.includes("Непредвиден") || verdict === "unexpected"
      ? "bg-red-100 text-red-800"
      : "bg-gray-100 text-gray-600";

  return (
    <div className="space-y-2">
      <p>
        <span className="font-medium">Вердикт:</span>{" "}
        <Badge className={verdictColor} variant="outline">
          {verdict ? labels.expectedness(verdict) || verdict : "Неизвестно"}
        </Badge>
        {ragUsed === false && (
          <span className="text-xs text-gray-500 ml-2">(ИМП не подгружен)</span>
        )}
      </p>
      {rationale && <p className="text-gray-600">{rationale}</p>}
      {sections.length > 0 && (
        <p className="text-xs text-gray-500">Релевантные разделы ИМП: {sections.join(", ")}</p>
      )}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function statusLabel(s: ReportStatus): string {
  switch (s) {
    case "submitted": return "На рассмотрении";
    case "clarification": return "На уточнении";
    case "analysis": return "В анализе";
    case "finalized": return "Финализирован";
  }
}
