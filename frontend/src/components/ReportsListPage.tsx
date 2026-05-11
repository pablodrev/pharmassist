import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { ReportCard } from "./ReportCard";
import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";
import { Input } from "./ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Button } from "./ui/button";
import { Search, Plus } from "lucide-react";
import { toast } from "sonner";

type ReportShort = components["schemas"]["ReportShortResponse"];
type ReportStatus = components["schemas"]["ReportStatus"];
type Severity = components["schemas"]["SeverityLevel"];
type DateRange = components["schemas"]["DateRangeFilter"];

interface ReportsListPageProps {
  onNewReport?: () => void;
  onOpenReport?: (reportId: string) => void;
  showNewButton?: boolean;
  title?: string;
}

const TABS: { value: ReportStatus; label: string }[] = [
  { value: "submitted", label: "Входящие" },
  { value: "clarification", label: "На уточнении" },
  { value: "analysis", label: "На анализе" },
  { value: "finalized", label: "Финализированы" },
];

export function ReportsListPage({
  onNewReport,
  onOpenReport,
  showNewButton = true,
  title = "ФармАссист",
}: ReportsListPageProps) {
  const [reports, setReports] = useState<ReportShort[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [dateFilter, setDateFilter] = useState<DateRange | "all">("all");
  const [activeTab, setActiveTab] = useState<ReportStatus>("submitted");

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    setLoading(true);

    // NB: backend currently ignores `search` and `severity` (см. reports.py:364).
    // Шлём всё равно — если поправят, клиентская фильтрация ниже станет no-op.
    const query: Record<string, unknown> = {
      status: activeTab,
      limit: 100,
    };
    if (searchQuery.trim()) query.search = searchQuery.trim();
    if (severityFilter !== "all") query.severity = severityFilter;
    if (dateFilter !== "all") query.date_range = dateFilter;

    const fetchOnce = (showSpinner: boolean) => {
      if (showSpinner) setLoading(true);
      return apiClient
        .GET("/api/v1/reports", { params: { query } })
        .then(({ data, error }) => {
          if (cancelled) return;
          if (error || !data) {
            if (showSpinner) toast.error("Не удалось загрузить список сообщений");
            setReports([]);
            return;
          }
          setReports(data.items);
          // Авто-поллинг пока есть pending-карточки (AI ещё анализирует)
          const hasPending = data.items.some(
            (r) => r.analysis_status === "pending",
          );
          if (hasPending && !cancelled) {
            pollTimer = setTimeout(() => fetchOnce(false), 5000);
          }
        })
        .finally(() => {
          if (!cancelled && showSpinner) setLoading(false);
        });
    };

    fetchOnce(true);

    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [activeTab, searchQuery, severityFilter, dateFilter]);

  // Клиентская фильтрация — компенсирует отсутствие search/severity на бэкенде.
  const visibleReports = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return reports.filter((r) => {
      if (severityFilter !== "all" && r.severity !== severityFilter) {
        return false;
      }
      if (q) {
        const haystack = [
          r.drug_name,
          r.adverse_reaction,
          r.reporter_name,
          r.id,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [reports, searchQuery, severityFilter]);

  return (
    <div className="min-h-screen bg-gray-50 bg-gradient_main">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 ">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="flex items-center justify-center">
                <h1>{title}</h1>
              </div>
              <p className="text-gray-600 mt-1 mx-2"></p>
            </div>
            {showNewButton && onNewReport && (
              <Button
                onClick={onNewReport}
                className="bg-blue-600 hover:bg-blue-200"
              >
                <Plus className="w-4 h-4 mr-2" />
                Новое сообщение
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Поиск по препарату или реакции..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select
              value={severityFilter}
              onValueChange={(v) => setSeverityFilter(v as Severity | "all")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все степени тяжести" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все степени тяжести</SelectItem>
                <SelectItem value="mild">Лёгкая</SelectItem>
                <SelectItem value="moderate">Средняя</SelectItem>
                <SelectItem value="severe">Тяжёлая</SelectItem>
                <SelectItem value="life-threatening">
                  Жизнеугрожающая
                </SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={dateFilter}
              onValueChange={(v) => setDateFilter(v as DateRange | "all")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все даты" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все даты</SelectItem>
                <SelectItem value="today">Сегодня</SelectItem>
                <SelectItem value="week">За неделю</SelectItem>
                <SelectItem value="month">За месяц</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as ReportStatus)}
          >
            <TabsList className="flex w-full">
              {TABS.map((t) => (
                <TabsTrigger key={t.value} value={t.value}>
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="space-y-4">
          {loading ? (
            <div className="text-center py-12 text-gray-500">Загрузка...</div>
          ) : visibleReports.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Сообщений не найдено</p>
            </div>
          ) : (
            visibleReports.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                onClick={() => {
                  if (onOpenReport) {
                    onOpenReport(report.id);
                  } else {
                    toast.info(
                      "Просмотр деталей доступен только специалистам (US-07 — позже)",
                    );
                  }
                }}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
