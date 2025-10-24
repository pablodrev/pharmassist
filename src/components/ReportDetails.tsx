import { Report } from "../types/report";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Textarea } from "./ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { X, Check, AlertCircle, Edit } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface ReportDetailsProps {
  report: Report;
  onClose: () => void;
  onStatusChange: (reportId: string, newStatus: Report["status"]) => void;
  onCompletenessChange?: (reportId: string, field: string, value: boolean) => void;
}

export function ReportDetails({ report, onClose, onStatusChange, onCompletenessChange }: ReportDetailsProps) {
  const [comment, setComment] = useState("");
  const [newStatus, setNewStatus] = useState(report.status);
  const [localCompleteness, setLocalCompleteness] = useState(report.completeness);

  const handleAddComment = () => {
    if (comment.trim()) {
      toast.success("Комментарий добавлен");
      setComment("");
    }
  };

  const handleStatusChange = () => {
    if (newStatus !== report.status) {
      onStatusChange(report.id, newStatus);
      toast.success("Статус изменен");
    }
  };

  const completenessItems = [
    { key: "patientInfo", label: "Информация о пациенте", value: report.completeness.patientInfo },
    { key: "doctorInfo", label: "Информация о враче", value: report.completeness.doctorInfo },
    {
      key: "medicationStartDate",
      label: "Дата начала приема препарата",
      value: report.completeness.medicationStartDate,
    },
    {
      key: "medicationEndDate",
      label: "Дата окончания приема препарата",
      value: report.completeness.medicationEndDate,
    },
    {
      key: "medicationBatch",
      label: "Номер серии препарата",
      value: report.completeness.medicationBatch,
    },
    {
      key: "effectDate",
      label: "Дата возникновения побочного эффекта",
      value: report.completeness.effectDate,
    },
    {
      key: "effectDescription",
      label: "Описание побочного эффекта",
      value: report.completeness.effectDescription,
    },
    { key: "severity", label: "Степень тяжести", value: report.completeness.severity },
    { key: "outcome", label: "Исход побочного эффекта", value: report.completeness.outcome },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 overflow-y-auto p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full my-8">
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between rounded-t-lg">
          <div>
            <h2 className="mb-1">Детали сообщения #{report.id}</h2>
            <p className="text-sm text-gray-500">
              Получено: {report.dateReceived.toLocaleDateString("ru-RU")}
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="p-6 space-y-6">
          {/* AI Notes */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-blue-600" />
              <h3 className="text-blue-900">Пометки от ИИ-ассистента</h3>
            </div>
            <div className="space-y-2">
              {report.aiNotes.map((note, index) => (
                <p key={index} className="text-sm text-blue-800">
                  • {note}
                </p>
              ))}
            </div>
          </div>

          {/* Patient Information */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="mb-4">Информация о пациенте</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">ФИО:</span>
                  <p className="font-medium">{report.patientName}</p>
                </div>
                <div>
                  <span className="text-gray-600">ID пациента:</span>
                  <p className="font-medium">{report.patientId}</p>
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-4">Информация о препарате</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">Название:</span>
                  <p className="font-medium">{report.medicationName}</p>
                </div>
                <div>
                  <span className="text-gray-600">Побочный эффект:</span>
                  <p className="font-medium">{report.adverseEffect}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Completeness Check */}
          <div>
            <h3 className="mb-4">Полнота данных</h3>
            <div className="grid grid-cols-2 gap-3">
              {completenessItems.map((item) => (
                <div
                  key={item.key}
                  onClick={() => {
                    const newValue = !localCompleteness[item.key as keyof typeof localCompleteness];
                    setLocalCompleteness({ ...localCompleteness, [item.key]: newValue });
                    onCompletenessChange?.(report.id, item.key, newValue);
                    toast.success(`Значение "${item.label}" изменено`);
                  }}
                  className="flex items-center gap-2 text-sm p-2 rounded border cursor-pointer hover:opacity-80 transition-opacity"
                  style={{
                    backgroundColor: localCompleteness[item.key as keyof typeof localCompleteness] ? "#f0fdf4" : "#fef2f2",
                    borderColor: localCompleteness[item.key as keyof typeof localCompleteness] ? "#86efac" : "#fca5a5",
                  }}
                >
                  {localCompleteness[item.key as keyof typeof localCompleteness] ? (
                    <Check className="w-4 h-4 text-green-600 shrink-0" />
                  ) : (
                    <X className="w-4 h-4 text-red-600 shrink-0" />
                  )}
                  <span className={localCompleteness[item.key as keyof typeof localCompleteness] ? "text-green-800" : "text-red-800"}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Status Change */}
          <div>
            <h3 className="mb-4">Изменить статус</h3>
            <div className="flex items-center gap-3">
              <Select value={newStatus} onValueChange={(val) => setNewStatus(val as Report["status"])}>
                <SelectTrigger className="w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="incoming">Входящие</SelectItem>
                  <SelectItem value="clarification">На уточнении</SelectItem>
                  <SelectItem value="analysis">Анализ</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={handleStatusChange}
                disabled={newStatus === report.status}
                className="bg-indigo-600 hover:bg-indigo-700"
              >
                Сохранить статус
              </Button>
            </div>
          </div>

          {/* Comments */}
          <div>
            <h3 className="mb-4">Добавить комментарий или заметку</h3>
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Введите ваш комментарий..."
              rows={4}
            />
            <Button
              onClick={handleAddComment}
              className="mt-3 bg-indigo-600 hover:bg-indigo-700"
            >
              Добавить комментарий
            </Button>
          </div>

          {/* Edit Button */}
          <div className="border-t pt-4">
            <Button variant="outline" className="w-full">
              <Edit className="w-4 h-4 mr-2" />
              Редактировать данные сообщения
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
