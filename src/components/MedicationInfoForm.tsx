import { useForm } from "react-hook-form";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
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

interface MedicationInfoFormProps {
  data: FormData;
  onNext: (data: Partial<FormData>) => void;
  onBack: () => void;
}

export function MedicationInfoForm({ data, onNext, onBack }: MedicationInfoFormProps) {
  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm({
    defaultValues: {
      tradeName: data.tradeName,
      innName: data.innName,
      dosageForm: data.dosageForm,
      dosage: data.dosage,
      dosageUnit: data.dosageUnit,
      frequency: data.frequency,
      administrationRoute: data.administrationRoute,
      startDate: data.startDate,
      endDate: data.endDate,
      prescriptionReason: data.prescriptionReason,
      batchNumber: data.batchNumber,
      manufacturer: data.manufacturer,
    },
  });

  const startDate = watch("startDate");
  const endDate = watch("endDate");
  const dosageForm = watch("dosageForm");
  const dosageUnit = watch("dosageUnit");
  const frequency = watch("frequency");
  const administrationRoute = watch("administrationRoute");

  const onSubmit = (formData: any) => {
    onNext(formData);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <h2 className="mb-6 font-medium">Информация о лекарственном препарате</h2>

        <div className="space-y-4">
          <div>
            <Label htmlFor="tradeName">Торговое название препарата *</Label>
            <Input
              id="tradeName"
              {...register("tradeName", { required: "Обязательное поле" })}
              placeholder="Например: Парацетамол"
            />
            {errors.tradeName && (
              <p className="text-sm text-red-500 mt-1">{errors.tradeName.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="innName">Международное непатентованное название (МНН) *</Label>
            <Input
              id="innName"
              {...register("innName", { required: "Обязательное поле" })}
              placeholder="Например: Paracetamol"
            />
            {errors.innName && (
              <p className="text-sm text-red-500 mt-1">{errors.innName.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="dosageForm">Лекарственная форма *</Label>
            <Select
              value={dosageForm}
              onValueChange={(value) => setValue("dosageForm", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите форму" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tablets">Таблетки</SelectItem>
                <SelectItem value="capsules">Капсулы</SelectItem>
                <SelectItem value="injection">Раствор для инъекций</SelectItem>
                <SelectItem value="ointment">Мазь</SelectItem>
                <SelectItem value="cream">Крем</SelectItem>
                <SelectItem value="syrup">Сироп</SelectItem>
                <SelectItem value="suspension">Суспензия</SelectItem>
                <SelectItem value="drops">Капли</SelectItem>
                <SelectItem value="spray">Спрей</SelectItem>
                <SelectItem value="other">Другое</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="dosage">Дозировка препарата *</Label>
              <Input
                id="dosage"
                type="number"
                step="0.01"
                {...register("dosage", { required: "Обязательное поле" })}
                placeholder="500"
              />
              {errors.dosage && (
                <p className="text-sm text-red-500 mt-1">{errors.dosage.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="dosageUnit">Единица измерения *</Label>
              <Select
                value={dosageUnit}
                onValueChange={(value) => setValue("dosageUnit", value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="мг">мг</SelectItem>
                  <SelectItem value="мкг">мкг</SelectItem>
                  <SelectItem value="г">г</SelectItem>
                  <SelectItem value="мл">мл</SelectItem>
                  <SelectItem value="ЕД">ЕД</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="frequency">Кратность приема *</Label>
            <Select
              value={frequency}
              onValueChange={(value) => setValue("frequency", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите кратность" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 раз в сутки</SelectItem>
                <SelectItem value="2">2 раза в сутки</SelectItem>
                <SelectItem value="3">3 раза в сутки</SelectItem>
                <SelectItem value="4">4 раза в сутки</SelectItem>
                <SelectItem value="other">Другая</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="administrationRoute">Способ введения/применения *</Label>
            <Select
              value={administrationRoute}
              onValueChange={(value) => setValue("administrationRoute", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите способ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="oral">Внутрь</SelectItem>
                <SelectItem value="iv">Внутривенно</SelectItem>
                <SelectItem value="im">Внутримышечно</SelectItem>
                <SelectItem value="sc">Подкожно</SelectItem>
                <SelectItem value="topical">Местно</SelectItem>
                <SelectItem value="rectal">Ректально</SelectItem>
                <SelectItem value="vaginal">Вагинально</SelectItem>
                <SelectItem value="inhalation">Ингаляционно</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Дата начала приема *</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {startDate ? (
                      startDate.toLocaleDateString('ru-RU')
                    ) : (
                      <span>Выберите дату</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={startDate}
                    onSelect={(date) => setValue("startDate", date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div>
              <Label>Дата окончания приема</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {endDate ? (
                      endDate.toLocaleDateString('ru-RU')
                    ) : (
                      <span>Выберите дату</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={endDate}
                    onSelect={(date) => setValue("endDate", date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div>
            <Label htmlFor="prescriptionReason">Причина назначения препарата *</Label>
            <Textarea
              id="prescriptionReason"
              {...register("prescriptionReason", { required: "Обязательное поле" })}
              placeholder="Краткое описание диагноза или симптома"
              rows={2}
            />
            {errors.prescriptionReason && (
              <p className="text-sm text-red-500 mt-1">{errors.prescriptionReason.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="batchNumber">Номер серии препарата</Label>
            <Input
              id="batchNumber"
              {...register("batchNumber")}
              placeholder="Если известен"
            />
          </div>

          <div>
            <Label htmlFor="manufacturer">Производитель препарата</Label>
            <Input
              id="manufacturer"
              {...register("manufacturer")}
              placeholder="Если известен"
            />
          </div>
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
