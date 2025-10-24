import { useForm } from "react-hook-form";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { FormData } from "../App";
import { useState } from "react";
import { Upload, X, FileIcon } from "lucide-react";
import { toast } from "sonner";

interface FilesAndAdditionalInfoFormProps {
  data: FormData;
  onSubmit: (data: Partial<FormData>) => void;
  onBack: () => void;
  onGoBackToFirst: () => void;
}

export function FilesAndAdditionalInfoForm({
  data,
  onSubmit,
  onBack,
}: FilesAndAdditionalInfoFormProps) {
  const { register, handleSubmit, setValue } = useForm({
    defaultValues: {
      additionalInfo: data.additionalInfo,
    },
  });

  const [files, setFiles] = useState<File[]>(data.files || []);
  const [fileDescriptions, setFileDescriptions] = useState<{ [key: string]: string }>(
    data.fileDescriptions || {}
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      const allowedTypes = [
        "image/jpeg",
        "image/png",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      ];

      const validFiles = newFiles.filter((file) => {
        if (!allowedTypes.includes(file.type)) {
          toast.error(`Файл ${file.name} имеет неподдерживаемый формат`);
          return false;
        }
        if (file.size > 10 * 1024 * 1024) {
          toast.error(`Файл ${file.name} слишком большой (максимум 10 МБ)`);
          return false;
        }
        return true;
      });

      setFiles([...files, ...validFiles]);
    }
  };

  const handleRemoveFile = (index: number) => {
    const fileName = files[index].name;
    const newFiles = files.filter((_, i) => i !== index);
    setFiles(newFiles);

    const newDescriptions = { ...fileDescriptions };
    delete newDescriptions[fileName];
    setFileDescriptions(newDescriptions);
  };

  const handleFileDescriptionChange = (fileName: string, description: string) => {
    setFileDescriptions({
      ...fileDescriptions,
      [fileName]: description,
    });
  };

  const onFormSubmit = (formData: any) => {
    onSubmit({
      ...formData,
      files,
      fileDescriptions,
    });
  };

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
      <div>
        <h2 className="mb-6 font-medium">Загрузка файлов и дополнительная информация</h2>

        <div className="space-y-6">
          <div>
            <Label htmlFor="fileUpload">Загрузка файлов</Label>
            <p className="text-sm text-gray-500 mb-2">
              Поддерживаемые форматы: JPG, PNG, PDF, DOCX, XLSX (максимум 10 МБ на файл)
            </p>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 transition-colors">
              <input
                id="fileUpload"
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.pdf,.docx,.xlsx"
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="fileUpload"
                className="cursor-pointer flex flex-col items-center"
              >
                <Upload className="w-12 h-12 text-gray-400 mb-2" />
                <span className="text-sm text-gray-600">
                  Нажмите для выбора файлов или перетащите их сюда
                </span>
              </label>
            </div>
          </div>

          {files.length > 0 && (
            <div className="space-y-3">
              <Label>Загруженные файлы ({files.length})</Label>
              {files.map((file, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <FileIcon className="w-5 h-5 text-indigo-600" />
                      <span className="text-sm">{file.name}</span>
                      <span className="text-xs text-gray-500">
                        ({(file.size / 1024).toFixed(2)} КБ)
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveFile(index)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                  <div>
                    <Input
                      placeholder="Описание файла (например: 'Результаты анализов')"
                      value={fileDescriptions[file.name] || ""}
                      onChange={(e) =>
                        handleFileDescriptionChange(file.name, e.target.value)
                      }
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          <div>
            <Label htmlFor="additionalInfo">Дополнительная информация</Label>
            <p className="text-sm text-gray-500 mb-2">
              Если вы хотите добавить какую-либо дополнительную информацию, пожалуйста,
              укажите ее здесь
            </p>
            <Textarea
              id="additionalInfo"
              {...register("additionalInfo")}
              placeholder="Любая дополнительная информация, которая может быть полезной..."
              rows={6}
            />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Обратите внимание:</strong> Вся предоставленная информация будет
              обработана в соответствии с требованиями конфиденциальности и использована
              исключительно в целях фармаконадзора для повышения безопасности применения
              лекарственных препаратов.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-between">
        <Button type="button" variant="outline" onClick={onBack}>
          Назад
        </Button>
        <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700">
          Отправить отчет
        </Button>
      </div>
    </form>
  );
}
