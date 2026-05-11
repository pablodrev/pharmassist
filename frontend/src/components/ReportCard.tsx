import type { components } from "../api/schema";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";
import { AlertCircle, Clock, CheckCircle2 } from "lucide-react";

type ReportShort = components["schemas"]["ReportShortResponse"];
type ReportStatus = components["schemas"]["ReportStatus"];

interface ReportCardProps {
  report: ReportShort;
  onClick: () => void;
}

const STATUS_BORDER: Record<ReportStatus, string> = {
  submitted: "#3b82f6",
  clarification: "#f59e0b",
  analysis: "#8b5cf6",
  finalized: "#10b981",
};

const SEVERITY_LABEL: Record<string, string> = {
  mild: "Лёгкая",
  moderate: "Средняя",
  severe: "Тяжёлая",
  "life-threatening": "Жизнеугрожающая",
};

const SEVERITY_COLOR: Record<string, string> = {
  mild: "bg-yellow-100 text-yellow-800",
  moderate: "bg-orange-100 text-orange-800",
  severe: "bg-red-100 text-red-800",
  "life-threatening": "bg-red-100 text-red-800",
};

export function ReportCard({ report, onClick }: ReportCardProps) {
  const created = new Date(report.created_at);
  const analysisStatus = report.analysis_status;

  return (
    <Card
      className="p-4 hover:shadow-lg transition-shadow cursor-pointer border-l-4"
      style={{ borderLeftColor: STATUS_BORDER[report.status] ?? "#9ca3af" }}
      onClick={onClick}
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold">
                {report.drug_name ?? "Препарат не определён"}
              </h3>
              <span className="text-xs text-gray-500">
                #{report.id.slice(0, 8)}
              </span>
            </div>
            {report.adverse_reaction && (
              <p className="text-sm text-gray-600 mt-1">
                {report.adverse_reaction}
              </p>
            )}
            {report.reporter_name && (
              <p className="text-xs text-gray-500 mt-1">
                Подал: {report.reporter_name}
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">
              {created.toLocaleDateString("ru-RU")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {report.severity && (
            <Badge
              className={SEVERITY_COLOR[report.severity] ?? "bg-gray-100"}
              variant="outline"
            >
              {SEVERITY_LABEL[report.severity] ?? report.severity}
            </Badge>
          )}
          {report.is_clinically_significant !== null &&
            report.is_clinically_significant !== undefined && (
              <Badge
                className={
                  report.is_clinically_significant
                    ? "bg-red-100 text-red-800"
                    : "bg-gray-100 text-gray-800"
                }
                variant="outline"
              >
                {report.is_clinically_significant
                  ? "Клинически значимо"
                  : "Не значимо"}
              </Badge>
            )}
          {analysisStatus === "pending" && (
            <Badge
              className="bg-blue-100 text-blue-800"
              variant="outline"
            >
              <Clock className="w-3 h-3 mr-1" /> AI анализирует...
            </Badge>
          )}
          {analysisStatus === "ready" && (
            <Badge
              className="bg-green-100 text-green-800"
              variant="outline"
            >
              <CheckCircle2 className="w-3 h-3 mr-1" /> AI готов
            </Badge>
          )}
          {analysisStatus === "failed" && (
            <Badge
              className="bg-red-100 text-red-800"
              variant="outline"
            >
              <AlertCircle className="w-3 h-3 mr-1" /> AI ошибка
            </Badge>
          )}
        </div>
      </div>
    </Card>
  );
}
