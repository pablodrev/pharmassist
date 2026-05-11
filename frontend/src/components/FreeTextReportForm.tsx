import { useState, type FormEvent } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { ArrowLeft } from "lucide-react";
import { apiClient } from "../api/client";
import { toast } from "sonner";

interface Props {
  onSubmitted: () => void;
  onBack: () => void;
}

const MIN_LENGTH = 10;

export function FreeTextReportForm({ onSubmitted, onBack }: Props) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (text.trim().length < MIN_LENGTH) {
      toast.error(`Описание должно быть не короче ${MIN_LENGTH} символов`);
      return;
    }
    setSubmitting(true);
    try {
      const { error } = await apiClient.POST("/api/v1/reports", {
        body: { raw_text: text.trim() },
      });
      if (error) {
        throw new Error(extractError(error) ?? "Не удалось отправить сообщение");
      }
      toast.success("Сообщение принято", {
        description: "AI начал анализ — результат появится в списке через ~15 секунд.",
      });
      onSubmitted();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка отправки");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 bg-gradient_main">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <Button variant="ghost" onClick={onBack} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Назад
          </Button>
        </div>

        <div className="mb-6 text-center">
          <h1 className="mb-3">Сообщение в свободной форме</h1>
          <p className="text-gray-600">
            Опишите случай побочной реакции своими словами. Укажите препарат,
            дозу, симптомы, даты и исход — AI постарается извлечь
            структурированные данные.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-lg shadow-lg p-8 space-y-4"
        >
          <div>
            <Label htmlFor="raw-text">Описание случая</Label>
            <Textarea
              id="raw-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={14}
              placeholder="Например: Пациент 54 лет начал приём Амоксициллина 500 мг 3 раза в день 10.05. На третий день появилась крапивница на руках и ногах, зуд. Препарат отменён 13.05, симптомы прошли через 2 дня."
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Минимум {MIN_LENGTH} символов. Сейчас: {text.trim().length}.
            </p>
          </div>

          <div className="flex gap-3 justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              disabled={submitting}
            >
              Отменить
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Отправка..." : "Отправить"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function extractError(err: unknown): string | null {
  if (!err) return null;
  if (typeof err === "string") return err;
  if (typeof err === "object" && err !== null) {
    const detail = (err as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  }
  return null;
}
