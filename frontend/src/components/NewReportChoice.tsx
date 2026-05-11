import { Button } from "./ui/button";
import { ArrowLeft, FileText, AlignLeft } from "lucide-react";

interface Props {
  onChooseForm: () => void;
  onChooseFreeText: () => void;
  onBack: () => void;
}

export function NewReportChoice({
  onChooseForm,
  onChooseFreeText,
  onBack,
}: Props) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 bg-gradient_main">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6">
          <Button variant="ghost" onClick={onBack} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Вернуться к списку
          </Button>
        </div>

        <div className="mb-8 text-center">
          <h1 className="mb-3">Новое сообщение о побочном эффекте</h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Выберите, как удобнее подать сообщение
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <button
            type="button"
            onClick={onChooseForm}
            className="bg-white rounded-lg shadow-lg p-8 text-left hover:shadow-xl transition-shadow border-2 border-transparent hover:border-blue-500"
          >
            <FileText className="w-10 h-10 text-blue-600 mb-4" />
            <h3 className="mb-2 font-semibold">Структурированная форма</h3>
            <p className="text-sm text-gray-600">
              Пятишаговая форма с полями о пациенте, враче, препарате и
              побочном эффекте.
            </p>
          </button>

          <button
            type="button"
            onClick={onChooseFreeText}
            className="bg-white rounded-lg shadow-lg p-8 text-left hover:shadow-xl transition-shadow border-2 border-transparent hover:border-blue-500"
          >
            <AlignLeft className="w-10 h-10 text-blue-600 mb-4" />
            <h3 className="mb-2 font-semibold">Свободный текст</h3>
            <p className="text-sm text-gray-600">
              Опишите случай в произвольной форме — AI извлечёт структурированные
              данные автоматически.
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}
