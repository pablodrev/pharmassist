import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";
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

type ReportResponse = components["schemas"]["ReportResponse"];
type ReportStatus = components["schemas"]["ReportStatus"];

interface Props {
  reportId: string;
  onBack: () => void;
  onFinalized: () => void;
}

type RecType = "completeness" | "ime" | "naranjo" | "expectedness";

interface Override {
  verdict: "accepted" | "edited";
  comment: string;
}

const REC_LABELS: Record<RecType, string> = {
  completeness: "Полнота информации",
  ime: "Клиническая значимость (IME)",
  naranjo: "Причинно-следственная связь (Наранжо)",
  expectedness: "Предвиденность (ИМП)",
};

export function SpecialistReviewPage({ reportId, onBack, onFinalized }: Props) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [overrides, setOverrides] = useState<Partial<Record<RecType, Override>>>(
    {},
  );
  const [editing, setEditing] = useState<Partial<Record<RecType, boolean>>>({});
  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [returning, setReturning] = useState(false);
  const [returnComment, setReturnComment] = useState("");
  const [showReturnModal, setShowReturnModal] = useState(false);

  // Initial load + auto-bump to "analysis" if still submitted
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const ensureAnalysisStatus = async (currentStatus: ReportStatus) => {
      if (currentStatus === "submitted") {
        await apiClient.PATCH("/api/v1/reports/{report_id}/status", {
          params: { path: { report_id: reportId } },
          body: { status: "analysis" },
        });
      }
    };

    const load = async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/reports/{report_id}",
        { params: { path: { report_id: reportId } } },
      );
      if (cancelled) return;
      if (error || !data) {
        toast.error("Не удалось загрузить отчёт");
        setLoading(false);
        return;
      }
      await ensureAnalysisStatus(data.status);
      setReport(data);
      setLoading(false);
      if (data.ai_recommendations.analysis_status !== "ready") {
        setPolling(true);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  // Poll analysis status until ready/failed
  useEffect(() => {
    if (!polling) return;
    let cancelled = false;
    const tick = async () => {
      const { data } = await apiClient.GET(
        "/api/v1/reports/{report_id}/analysis-status",
        { params: { path: { report_id: reportId } } },
      );
      if (cancelled) return;
      if (data?.analysis_status === "ready") {
        // refetch full report
        const { data: full } = await apiClient.GET(
          "/api/v1/reports/{report_id}",
          { params: { path: { report_id: reportId } } },
        );
        if (!cancelled && full) {
          setReport(full);
          setPolling(false);
        }
      } else if (data?.analysis_status === "failed") {
        toast.error("AI-анализ завершился ошибкой: " + (data.error ?? ""));
        setPolling(false);
      } else {
        setTimeout(tick, 3000);
      }
    };
    const handle = setTimeout(tick, 3000);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [polling, reportId]);

  const recs = report?.ai_recommendations;
  const allCaptured = useMemo(() => {
    if (!recs) return false;
    const types: RecType[] = ["completeness", "ime", "naranjo", "expectedness"];
    return types.every((t) => {
      // Если рекомендации этого типа нет (например, expectedness пропущен) —
      // считаем "captured" автоматически.
      if (!recs[t]) return true;
      return Boolean(overrides[t]);
    });
  }, [recs, overrides]);

  const handleAccept = (type: RecType) => {
    setOverrides((o) => {
      const next = { ...o };
      // повторный клик по "Принять" — снимает принятие
      if (next[type]?.verdict === "accepted") {
        delete next[type];
      } else {
        next[type] = { verdict: "accepted", comment: "" };
      }
      return next;
    });
    setEditing((e) => ({ ...e, [type]: false }));
  };

  const handleStartEdit = (type: RecType) => {
    // повторный клик по "Редактировать" — закрывает режим редактирования
    // и снимает правку, если она ещё не сохранена
    if (editing[type]) {
      setEditing((e) => ({ ...e, [type]: false }));
      setOverrides((o) => {
        if (o[type]?.verdict !== "edited") return o;
        const next = { ...o };
        delete next[type];
        return next;
      });
      return;
    }
    setEditing((e) => ({ ...e, [type]: true }));
    if (!overrides[type]) {
      setOverrides((o) => ({
        ...o,
        [type]: { verdict: "edited", comment: "" },
      }));
    }
  };

  const handleCommentChange = (type: RecType, comment: string) => {
    setOverrides((o) => ({
      ...o,
      [type]: { verdict: "edited", comment },
    }));
  };

  const handleSaveOverrides = async () => {
    setSaving(true);
    try {
      const body: Record<RecType, { verdict: string; comment: string } | null> =
        {
          completeness: overrides.completeness ?? null,
          ime: overrides.ime ?? null,
          naranjo: overrides.naranjo ?? null,
          expectedness: overrides.expectedness ?? null,
        };
      const { error } = await apiClient.PATCH(
        "/api/v1/reports/{report_id}/specialist-review",
        {
          params: { path: { report_id: reportId } },
          body: body as components["schemas"]["SpecialistReviewRequest"],
        },
      );
      if (error) throw new Error("Не удалось сохранить правки");
      toast.success("Правки сохранены");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  const handleFinalize = async () => {
    if (!allCaptured) {
      toast.error("Сначала примите или отредактируйте все рекомендации");
      return;
    }
    setFinalizing(true);
    try {
      // сначала сохраняем правки, затем финализируем
      await handleSaveOverrides();
      const { error } = await apiClient.POST(
        "/api/v1/reports/{report_id}/finalize",
        { params: { path: { report_id: reportId } } },
      );
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
    if (returnComment.trim().length === 0) {
      toast.error("Укажите причину возврата");
      return;
    }
    setReturning(true);
    try {
      const { error } = await apiClient.PATCH(
        "/api/v1/reports/{report_id}/status",
        {
          params: { path: { report_id: reportId } },
          body: { status: "clarification", comment: returnComment.trim() },
        },
      );
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

  // Pre-fill the return comment with missing fields from completeness rec
  const missingFieldsFromAI = useMemo(() => {
    const c = recs?.completeness as
      | {
          missing_mandatory_fields?: string[];
          warnings?: string[];
        }
      | undefined
      | null;
    if (!c) return "";
    const lines: string[] = [];
    if (c.missing_mandatory_fields?.length)
      lines.push(
        "Не хватает данных: " + c.missing_mandatory_fields.join(", "),
      );
    if (c.warnings?.length) lines.push(...c.warnings);
    return lines.join("\n");
  }, [recs]);

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
            <ArrowLeft className="w-4 h-4 mr-2" />
            Вернуться к очереди
          </Button>
        </div>

        {/* Report header */}
        <Card className="p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold mb-1">
                {report.drug?.name_ru ?? "Препарат не определён"}
              </h2>
              <p className="text-sm text-gray-500">
                #{report.id.slice(0, 8)} •{" "}
                {new Date(report.created_at).toLocaleString("ru-RU")}
              </p>
            </div>
            <Badge variant="outline">{statusLabel(report.status)}</Badge>
          </div>

          <div className="bg-gray-50 rounded p-4 mb-4">
            <p className="text-sm text-gray-600 mb-1 font-medium">
              Исходный текст сообщения:
            </p>
            <p className="text-sm whitespace-pre-wrap">{report.raw_text}</p>
          </div>

          {report.extracted_data && (
            <ExtractedDataView data={report.extracted_data} />
          )}
        </Card>

        {/* AI status banner */}
        {recs?.analysis_status !== "ready" && (
          <Card className="p-4 mb-6 bg-blue-50 border-blue-200">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              <div>
                <p className="font-medium text-blue-900">AI ещё анализирует</p>
                <p className="text-sm text-blue-700">
                  Рекомендации появятся через несколько секунд. Статус
                  обновляется автоматически.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* AI recommendations */}
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
                />
              ))}

            <div className="flex flex-wrap gap-3 justify-end pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => {
                  setReturnComment(missingFieldsFromAI);
                  setShowReturnModal(true);
                }}
                disabled={
                  report.status === "finalized" ||
                  report.status === "clarification"
                }
              >
                <Send className="w-4 h-4 mr-2" /> Вернуть на доработку
              </Button>
              <Button
                variant="outline"
                onClick={handleSaveOverrides}
                disabled={saving}
              >
                {saving ? "Сохранение..." : "Сохранить правки"}
              </Button>
              <Button
                onClick={handleFinalize}
                disabled={
                  !allCaptured || finalizing || report.status === "finalized"
                }
              >
                <Archive className="w-4 h-4 mr-2" />
                {finalizing ? "Финализация..." : "Финализировать"}
              </Button>
            </div>
            {!allCaptured && (
              <p className="text-xs text-gray-500 text-right">
                Чтобы финализировать, примите или отредактируйте каждую
                рекомендацию.
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
                Комментарий будет виден медработнику. Можно скорректировать
                автоматически подставленный список недостающих полей.
              </p>
              <Textarea
                value={returnComment}
                onChange={(e) => setReturnComment(e.target.value)}
                rows={6}
                placeholder="Опишите, что нужно дополнить..."
              />
              <div className="flex justify-end gap-2 mt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowReturnModal(false)}
                  disabled={returning}
                >
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

// ---------- Sub-components ----------

function RecommendationCard({
  type,
  data,
  override,
  isEditing,
  onAccept,
  onEdit,
  onCommentChange,
}: {
  type: RecType;
  data: Record<string, unknown>;
  override?: Override;
  isEditing: boolean;
  onAccept: () => void;
  onEdit: () => void;
  onCommentChange: (c: string) => void;
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
          <Button
            size="sm"
            variant={override?.verdict === "accepted" ? "default" : "outline"}
            onClick={onAccept}
          >
            <CheckCircle2 className="w-4 h-4 mr-1" /> Принять
          </Button>
          <Button
            size="sm"
            variant={isEditing ? "default" : "outline"}
            onClick={onEdit}
          >
            <Edit3 className="w-4 h-4 mr-1" /> Редактировать
          </Button>
        </div>
      </div>

      <div className="text-sm space-y-2">{renderRec(type, data)}</div>

      {isEditing && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-1">
            Комментарий специалиста (сохранится вместе с правкой):
          </p>
          <Textarea
            value={override?.comment ?? ""}
            onChange={(e) => onCommentChange(e.target.value)}
            rows={3}
            placeholder="Например: реакция указана в ИМП в разделе 4.8, но я считаю её непредвиденной из-за..."
          />
        </div>
      )}
    </Card>
  );
}

function renderRec(type: RecType, data: Record<string, unknown>) {
  switch (type) {
    case "completeness":
      return <CompletenessView data={data} />;
    case "ime":
      return <IMEView data={data} />;
    case "naranjo":
      return <NaranjoView data={data} />;
    case "expectedness":
      return <ExpectednessView data={data} />;
  }
}

function CompletenessView({ data }: { data: Record<string, unknown> }) {
  const missing = (data.missing_mandatory_fields as string[] | undefined) ?? [];
  const warnings = (data.warnings as string[] | undefined) ?? [];
  if (missing.length === 0 && warnings.length === 0) {
    return (
      <p className="text-green-700">
        ✓ Все обязательные поля заполнены, замечаний нет.
      </p>
    );
  }
  return (
    <div>
      {missing.length > 0 && (
        <div className="mb-2">
          <p className="text-gray-700 font-medium">Не хватает данных:</p>
          <ul className="list-disc list-inside text-gray-600">
            {missing.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div>
          <p className="text-gray-700 font-medium">Предупреждения:</p>
          <ul className="list-disc list-inside text-gray-600">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

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
          <Badge className="bg-gray-100" variant="outline">
            Не значимо
          </Badge>
        )}
      </p>
      {extracted.length > 0 && (
        <p className="text-gray-600">
          <span className="font-medium">Извлечённые реакции:</span>{" "}
          {extracted.join(", ")}
        </p>
      )}
      {matches.length > 0 && (
        <div>
          <p className="font-medium text-gray-700">Совпадения с EMA IME:</p>
          <ul className="list-disc list-inside text-gray-600">
            {matches.map((m, i) => (
              <li key={i}>
                {String(m.pt_name ?? m.reaction ?? "—")}{" "}
                {m.score !== undefined && (
                  <span className="text-xs text-gray-400">
                    (score: {Number(m.score).toFixed(2)})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {notInIme.length > 0 && (
        <p className="text-gray-500 text-xs">
          Реакции, не найденные в IME: {notInIme.join(", ")}
        </p>
      )}
    </div>
  );
}

function NaranjoView({ data }: { data: Record<string, unknown> }) {
  const score = data.total_score as number | undefined;
  const verdict = data.verdict as string | undefined;
  const confidence = data.confidence as string | undefined;
  const missing = (data.missing_data_for_assessment as string[] | undefined) ?? [];
  return (
    <div className="space-y-2">
      <p>
        <span className="font-medium">Балл:</span> {score ?? "—"} /{" "}
        <span className="font-medium">Вердикт:</span>{" "}
        <Badge className="bg-blue-100 text-blue-800" variant="outline">
          {verdict ? labels.naranjoVerdict(verdict) : "—"}
        </Badge>
        {confidence && (
          <span className="text-xs text-gray-500 ml-2">
            (уверенность: {confidence})
          </span>
        )}
      </p>
      {missing.length > 0 && (
        <p className="text-gray-500 text-xs">
          Не хватает данных: {missing.join(", ")}
        </p>
      )}
    </div>
  );
}

function ExpectednessView({ data }: { data: Record<string, unknown> }) {
  const verdict = data.verdict as string | undefined;
  const rationale = data.rationale as string | undefined;
  const sections = (data.relevant_smp_sections as string[] | undefined) ?? [];
  const ragUsed = data.rag_used as boolean | undefined;
  return (
    <div className="space-y-2">
      <p>
        <span className="font-medium">Вердикт:</span>{" "}
        <Badge
          className={
            verdict === "expected"
              ? "bg-yellow-100 text-yellow-800"
              : verdict === "unexpected"
                ? "bg-red-100 text-red-800"
                : "bg-gray-100"
          }
          variant="outline"
        >
          {labels.expectedness(verdict) || "Неизвестно"}
        </Badge>
        {ragUsed === false && (
          <span className="text-xs text-gray-500 ml-2">
            (ИМП не подгружен)
          </span>
        )}
      </p>
      {rationale && <p className="text-gray-600">{rationale}</p>}
      {sections.length > 0 && (
        <p className="text-xs text-gray-500">
          Релевантные разделы ИМП: {sections.join(", ")}
        </p>
      )}
    </div>
  );
}

function ExtractedDataView({
  data,
}: {
  data: components["schemas"]["ExtractedCaseData"];
}) {
  const p = data.patient as Record<string, unknown> | undefined;
  const drug = data.suspect_drug as Record<string, unknown> | undefined;
  const r = data.adverse_reaction as Record<string, unknown> | undefined;

  const patientParts = [
    p?.name && String(p.name),
    p?.age && `${p.age} лет`,
    labels.sex(p?.sex),
    p?.weight && `${p.weight} кг`,
  ].filter(Boolean);

  const drugParts = [
    drug?.name && String(drug.name),
    drug?.dose && String(drug.dose),
    labels.route(drug?.route),
    labels.dosageForm(drug?.form),
  ].filter(Boolean);

  return (
    <div className="grid md:grid-cols-3 gap-4 text-sm">
      <div>
        <p className="font-medium text-gray-700 mb-1">Пациент</p>
        <p className="text-gray-600">
          {patientParts.length ? patientParts.join(", ") : "—"}
        </p>
        {p?.diagnosis && (
          <p className="text-gray-500 text-xs mt-1">
            Диагноз: {String(p.diagnosis)}
          </p>
        )}
      </div>
      <div>
        <p className="font-medium text-gray-700 mb-1">Препарат</p>
        <p className="text-gray-600">
          {drugParts.length ? drugParts.join(", ") : "—"}
        </p>
        {drug?.indication && (
          <p className="text-gray-500 text-xs mt-1">
            Показание: {String(drug.indication)}
          </p>
        )}
        {drug?.action_taken && (
          <p className="text-gray-500 text-xs mt-1">
            Действия: {formatActionTaken(drug.action_taken)}
          </p>
        )}
      </div>
      <div>
        <p className="font-medium text-gray-700 mb-1">Реакция</p>
        <p className="text-gray-600">
          {r?.description ? String(r.description) : "—"}
        </p>
        <div className="text-gray-500 text-xs mt-1 space-y-0.5">
          {r?.severity && (
            <p>Тяжесть: {labels.severity(r.severity)}</p>
          )}
          {r?.outcome && <p>Исход: {labels.outcome(r.outcome)}</p>}
          {r?.is_serious !== undefined && r?.is_serious !== null && (
            <p>Серьёзная: {labels.yesNo(r.is_serious)}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function statusLabel(s: ReportStatus): string {
  switch (s) {
    case "submitted":
      return "На рассмотрении";
    case "clarification":
      return "На уточнении";
    case "analysis":
      return "В анализе";
    case "finalized":
      return "Финализирован";
  }
}

