import { Report } from "../types/report";
import { Badge } from "./ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./ui/card";
import { AlertCircle, CheckCircle, Clock, Check } from "lucide-react";

interface ReportCardProps {
  report: Report;
  onClick: () => void;
}

export function ReportCard({ report, onClick }: ReportCardProps) {
  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case "mild":
        return "bg-yellow-100 text-yellow-800";
      case "moderate":
        return "bg-orange-100 text-orange-800";
      case "severe":
      case "life-threatening":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getCausalityColor = (causality?: string) => {
    switch (causality) {
      case "certain":
        return "bg-red-100 text-red-800";
      case "probable":
        return "bg-orange-100 text-orange-800";
      case "possible":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getClinicalSignificanceColor = (level?: string) => {
    switch (level) {
      case "familiar":
        return "bg-red-100 text-red-800";
      case "iunfamiliar":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const GetColorForesight = (probability?: string) => {
    switch (probability) {
      case "foreseen":
        return "bg-yellow-100 text-green-800";
      case "notForeseen":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };


  const completenessPercentage = () => {
    const values = Object.values(report.completeness);
    const completed = values.filter(Boolean).length;
    return Math.round((completed / values.length) * 100);
  };

  const percentage = completenessPercentage();

  return (
    <Card
      className="p-4 hover:shadow-lg transition-shadow cursor-pointer border-l-4"
      style={{
        borderLeftColor:
          report.status === "incoming"
            ? "#3b82f6"
            : report.status === "clarification"
              ? "#f59e0b"
              : "#10b981",
      }}
      onClick={onClick}
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold flex items-center gap-2">
                {report.patientName}
              </h3>
              <span className="flex items-center gap-2 text-sm text-gray-500">#{report.id}{report.confirmed && <Check className="w-5 h-5 text-green-600" />}</span>
            </div>
            <p className="text-sm text-gray-600">
              Препарат: <span className="font-medium">{report.medicationName}</span>
            </p>
            <p className="text-sm text-gray-600 mt-1">{report.adverseEffect}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">
              {report.dateReceived.toLocaleDateString("ru-RU")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {report.severity && (
            <Badge className={getSeverityColor(report.severity)} variant="outline">
              {report.severity === "mild"
                ? "Удовлетворительное"
                : report.severity === "moderate"
                  ? "Средняя степень"
                  : report.severity === "severe"
                    ? "Тяжелая"
                    : "Жизнеугрожающая"}
            </Badge>
          )}
          {report.causalityAssessment && (
            <Badge
              className={getCausalityColor(report.causalityAssessment)}
              variant="outline"
            >
              {report.causalityAssessment === "certain"
                ? "Определенная связь"
                : report.causalityAssessment === "probable"
                  ? "Вероятная связь"
                  : "Возможная связь"}
            </Badge>
          )}
          {report.clinicalSignificance && (
            <Badge
              className={getClinicalSignificanceColor(report.clinicalSignificance)}
              variant="outline"
            >
              {report.clinicalSignificance === "familiar"
                ? "Значимо"
                : "Незначимое"}
            </Badge>
          )}
          {report.definitionForesight && (
            <Badge
              className={GetColorForesight(report.definitionForesight)}
              variant="outline"
            >
              {report.definitionForesight === "foreseen"
                ? "Предвиденное"
                : "Непредвиденное"}
            </Badge>
          )}
        </div>

        {/* AI Notes */}
        {report.status !== "analysis" && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-1">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900">Пометки от ИИ-ассистента:</span>
            </div>
            {report.aiNotes.map((note, index) => (
              <p key={index} className="text-sm text-blue-800 pl-6">
                • {note}
              </p>
            ))}
          </div>
        )}

        {/* Completeness indicator */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Полнота данных:</span>
            <span className="font-medium">{percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all"
              style={{
                width: `${percentage}%`,
                backgroundColor:
                  percentage >= 80
                    ? "#10b981"
                    : percentage >= 50
                      ? "#f59e0b"
                      : "#ef4444",
              }}
            />
          </div>
        </div>
      </div>
    </Card>
  );
}
