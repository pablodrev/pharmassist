import { useForm } from "react-hook-form@7.55.0";
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

interface PatientInfoFormProps {
  data: FormData;
  onNext: (data: Partial<FormData>) => void;
}

export function PatientInfoForm({ data, onNext }: PatientInfoFormProps) {
  const { register, handleSubmit, formState: { errors }, setValue, watch } = useForm({
    defaultValues: {
      patientName: data.patientName,
      patientGender: data.patientGender,
      patientAge: data.patientAge,
      patientBirthDate: data.patientBirthDate,
      patientWeight: data.patientWeight,
      primaryDiagnosis: data.primaryDiagnosis,
      comorbidities: data.comorbidities,
    },
  });

  const patientBirthDate = watch("patientBirthDate");
  const patientGender = watch("patientGender");

  const onSubmit = (formData: any) => {
    onNext(formData);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <h2 className="mb-6">Информация о пациенте</h2>

        <div className="space-y-4">
          <div>
            <Label htmlFor="patientName">ФИО пациента *</Label>
            <Input
              id="patientName"
              {...register("patientName", { required: "Обязательное поле" })}
              placeholder="Иванов Иван Иванович"
            />
            {errors.patientName && (
              <p className="text-sm text-red-500 mt-1">{errors.patientName.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="patientGender">Пол *</Label>
            <Select
              value={patientGender}
              onValueChange={(value) => setValue("patientGender", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите пол" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="male">Мужской</SelectItem>
                <SelectItem value="female">Женский</SelectItem>
              </SelectContent>
            </Select>
            {errors.patientGender && (
              <p className="text-sm text-red-500 mt-1">{errors.patientGender.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="patientAge">Возраст (лет) *</Label>
              <Input
                id="patientAge"
                type="number"
                {...register("patientAge", { required: "Обязательное поле" })}
                placeholder="35"
              />
              {errors.patientAge && (
                <p className="text-sm text-red-500 mt-1">{errors.patientAge.message}</p>
              )}
            </div>

            <div>
              <Label>Дата рождения *</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {patientBirthDate ? (
                      patientBirthDate.toLocaleDateString('ru-RU')
                    ) : (
                      <span>Выберите дату</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={patientBirthDate}
                    onSelect={(date) => setValue("patientBirthDate", date)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div>
            <Label htmlFor="patientWeight">Вес (кг) *</Label>
            <Input
              id="patientWeight"
              type="number"
              step="0.1"
              {...register("patientWeight", { required: "Обязательное поле" })}
              placeholder="70"
            />
            {errors.patientWeight && (
              <p className="text-sm text-red-500 mt-1">{errors.patientWeight.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="primaryDiagnosis">Основной диагноз *</Label>
            <Input
              id="primaryDiagnosis"
              {...register("primaryDiagnosis", { required: "Обязательное поле" })}
              placeholder="Заболевание, по поводу которого назначено лекарство"
            />
            {errors.primaryDiagnosis && (
              <p className="text-sm text-red-500 mt-1">{errors.primaryDiagnosis.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="comorbidities">Сопутствующие заболевания</Label>
            <Textarea
              id="comorbidities"
              {...register("comorbidities")}
              placeholder="Другие заболевания, которые есть у пациента"
              rows={3}
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700">
          Далее
        </Button>
      </div>
    </form>
  );
}