import { useForm } from "react-hook-form@7.55.0";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Checkbox } from "./ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Calendar } from "./ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import { CalendarIcon } from "lucide-react";
import { FormData } from "../App";
import { useState } from "react";

interface AdverseEffectInfoFormProps {
  data: FormData;
  onNext: (data: Partial<FormData>) => void;
  onBack: () => void;
}

export function AdverseEffectInfoForm({ data, onNext, onBack }: AdverseEffectInfoFormProps) {
  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm({
    defaultValues: {
      effectDate: data.effectDate,
      effectTime: data.effectTime,
      effectDescription: data.effectDescription,
      effectLocalization: data.effectLocalization,
      severity: data.severity,
      severityCriteria: data.severityCriteria,
      actionsTaken: data.actionsTaken,
      treatmentDescription: data.treatmentDescription,
      outcome: data.outcome,
      outcomeDate: data.outcomeDate,
      previousReactions: data.previousReactions,
      previousReactionsDescription: data.previousReactionsDescription,
      causalityAssessment: data.causalityAssessment,
      causalityFactors: data.causalityFactors,
    },
  });

  const [selectedActions, setSelectedActions] = useState<string[]>(data.actionsTaken);

  const effectDate = watch("effectDate");
  const outcomeDate = watch("outcomeDate");
  const severity = watch("severity");
  const outcome = watch("outcome");
  const previousReactions = watch("previousReactions");
  const causalityAssessment = watch("causalityAssessment");

  const actions = [
    { id: "discontinuation", label: "Отмена препарата" },
    { id: "doseReduction", label: "Снижение дозы" },
    { id: "treatment", label: "Назначение лечения" },
    { id: "hospitalization", label: "Госпитализация" },
    { id: "other", label: "Другие" },
  ];

  const handleActionChange = (actionId: string, checked: boolean) => {
    const newActions = checked
      ? [...selectedActions, actionId]
      : selectedActions.filter((id) => id !== actionId);
    setSelectedActions(newActions);
    setValue("actionsTaken", newActions);
  };

  const onSubmit = (formData: any) => {
    onNext({ ...formData, actionsTaken: selectedActions });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <h2 className="mb-6">Информация о побочном эффекте</h2>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Дата возникновения побочного эффекта *</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {effectDate ? (
                      effectDate.toLocaleDateString('ru-RU')
                    ) : (
                      <span>Выберите дату</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={effectDate}
                    onSelect={(date) => setValue("effectDate", date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div>
              <Label htmlFor="effectTime">Время возникновения (примерно)</Label>
              <Input
                id="effectTime"
                type="time"
                {...register("effectTime")}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="effectDescription">Подробное описание побочного эффекта *</Label>
            <Textarea
              id="effectDescription"
              {...register("effectDescription", { required: "Обязательное поле" })}
              placeholder="Пожалуйста, укажите все симптомы, их интенсивность и продолжительность"
              rows={5}
            />
            {errors.effectDescription && (
              <p className="text-sm text-red-500 mt-1">{errors.effectDescription.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="effectLocalization">Локализация побочного эффекта</Label>
            <Input
              id="effectLocalization"
              {...register("effectLocalization")}
              placeholder="Например: кожа, ЖКТ, нервная система"
            />
          </div>

          <div>
            <Label htmlFor="severity">Степень тяжести побочного эффекта *</Label>
            <Select
              value={severity}
              onValueChange={(value) => setValue("severity", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите степень" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mild">Легкая - минимальное влияние на повседневную активность</SelectItem>
                <SelectItem value="moderate">Средняя - значительное влияние на активность</SelectItem>
                <SelectItem value="severe">Тяжелая - невозможность выполнять обычные действия</SelectItem>
                <SelectItem value="life-threatening">Жизнеугрожающая - риск для жизни пациента</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="severityCriteria">Критерии определения степени тяжести</Label>
            <Textarea
              id="severityCriteria"
              {...register("severityCriteria")}
              placeholder='Например: "Нарушение повседневной активности", "Требовалась госпитализация"'
              rows={2}
            />
          </div>

          <div>
            <Label>Действия, предпринятые в связи с побочным эффектом *</Label>
            <div className="space-y-2 mt-2">
              {actions.map((action) => (
                <div key={action.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={action.id}
                    checked={selectedActions.includes(action.id)}
                    onCheckedChange={(checked) =>
                      handleActionChange(action.id, checked as boolean)
                    }
                  />
                  <Label htmlFor={action.id} className="cursor-pointer">
                    {action.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div>
            <Label htmlFor="treatmentDescription">Описание назначенного лечения</Label>
            <Textarea
              id="treatmentDescription"
              {...register("treatmentDescription")}
              placeholder="Если применялось лечение побочного эффекта"
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="outcome">Исход побочного эффекта *</Label>
            <Select
              value={outcome}
              onValueChange={(value) => setValue("outcome", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите исход" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recovered">Выздоровление</SelectItem>
                <SelectItem value="improving">Улучшение</SelectItem>
                <SelectItem value="unchanged">Без изменений</SelectItem>
                <SelectItem value="worsening">Ухудшение</SelectItem>
                <SelectItem value="death">Смерть</SelectItem>
                <SelectItem value="unknown">Неизвестно</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Дата наступления исхода</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start text-left"
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {outcomeDate ? (
                    outcomeDate.toLocaleDateString('ru-RU')
                  ) : (
                    <span>Выберите дату</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={outcomeDate}
                  onSelect={(date) => setValue("outcomeDate", date)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          <div>
            <Label htmlFor="previousReactions">Были ли ранее у пациента подобные реакции? *</Label>
            <Select
              value={previousReactions}
              onValueChange={(value) => setValue("previousReactions", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите вариант" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Да</SelectItem>
                <SelectItem value="no">Нет</SelectItem>
                <SelectItem value="unknown">Неизвестно</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {previousReactions === "yes" && (
            <div>
              <Label htmlFor="previousReactionsDescription">Описание предыдущих реакций</Label>
              <Textarea
                id="previousReactionsDescription"
                {...register("previousReactionsDescription")}
                placeholder="Опишите предыдущие реакции на данный препарат или другие лекарства"
                rows={3}
              />
            </div>
          )}

          <div>
            <Label htmlFor="causalityAssessment">Предполагаемая связь между препаратом и побочным эффектом *</Label>
            <Select
              value={causalityAssessment}
              onValueChange={(value) => setValue("causalityAssessment", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите оценку" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="certain">Определенная</SelectItem>
                <SelectItem value="probable">Вероятная</SelectItem>
                <SelectItem value="possible">Возможная</SelectItem>
                <SelectItem value="doubtful">Сомнительная</SelectItem>
                <SelectItem value="absent">Отсутствует</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {(causalityAssessment === "probable" || causalityAssessment === "possible") && (
            <div>
              <Label htmlFor="causalityFactors">Факторы, подтверждающие или опровергающие связь</Label>
              <Textarea
                id="causalityFactors"
                {...register("causalityFactors")}
                placeholder="Укажите факторы, которые подтверждают или опровергают причинно-следственную связь"
                rows={3}
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-between">
        <Button type="button" variant="outline" onClick={onBack}>
          Назад
        </Button>
        <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700">
          Далее
        </Button>
      </div>
    </form>
  );
}
