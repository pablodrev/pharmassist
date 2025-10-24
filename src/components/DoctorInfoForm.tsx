import { useForm } from "react-hook-form@7.55.0";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { FormData } from "../App";

interface DoctorInfoFormProps {
  data: FormData;
  onNext: (data: Partial<FormData>) => void;
  onBack: () => void;
}

export function DoctorInfoForm({ data, onNext, onBack }: DoctorInfoFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: {
      doctorName: data.doctorName,
      doctorPosition: data.doctorPosition,
      doctorSpecialty: data.doctorSpecialty,
      medicalInstitution: data.medicalInstitution,
      doctorPhone: data.doctorPhone,
      doctorEmail: data.doctorEmail,
    },
  });

  const onSubmit = (formData: any) => {
    onNext(formData);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <h2 className="mb-6">Информация о враче</h2>

        <div className="space-y-4">
          <div>
            <Label htmlFor="doctorName">ФИО врача *</Label>
            <Input
              id="doctorName"
              {...register("doctorName", { required: "Обязательное поле" })}
              placeholder="Петров Петр Петрович"
            />
            {errors.doctorName && (
              <p className="text-sm text-red-500 mt-1">{errors.doctorName.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="doctorPosition">Должность *</Label>
            <Input
              id="doctorPosition"
              {...register("doctorPosition", { required: "Обязательное поле" })}
              placeholder="Врач-терапевт"
            />
            {errors.doctorPosition && (
              <p className="text-sm text-red-500 mt-1">{errors.doctorPosition.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="doctorSpecialty">Специальность *</Label>
            <Input
              id="doctorSpecialty"
              {...register("doctorSpecialty", { required: "Обязательное поле" })}
              placeholder="Терапия"
            />
            {errors.doctorSpecialty && (
              <p className="text-sm text-red-500 mt-1">{errors.doctorSpecialty.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="medicalInstitution">Название медицинского учреждения *</Label>
            <Input
              id="medicalInstitution"
              {...register("medicalInstitution", { required: "Обязательное поле" })}
              placeholder="ГБУЗ Городская поликлиника №1"
            />
            {errors.medicalInstitution && (
              <p className="text-sm text-red-500 mt-1">{errors.medicalInstitution.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="doctorPhone">Контактный телефон *</Label>
            <Input
              id="doctorPhone"
              type="tel"
              {...register("doctorPhone", { required: "Обязательное поле" })}
              placeholder="+7 (999) 123-45-67"
            />
            {errors.doctorPhone && (
              <p className="text-sm text-red-500 mt-1">{errors.doctorPhone.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="doctorEmail">Электронная почта *</Label>
            <Input
              id="doctorEmail"
              type="email"
              {...register("doctorEmail", {
                required: "Обязательное поле",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Неверный формат email",
                },
              })}
              placeholder="doctor@example.com"
            />
            {errors.doctorEmail && (
              <p className="text-sm text-red-500 mt-1">{errors.doctorEmail.message}</p>
            )}
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
