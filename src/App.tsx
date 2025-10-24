import { useState } from "react";
import { PatientInfoForm } from "./components/PatientInfoForm";
import { DoctorInfoForm } from "./components/DoctorInfoForm";
import { MedicationInfoForm } from "./components/MedicationInfoForm";
import { AdverseEffectInfoForm } from "./components/AdverseEffectInfoForm";
import { FilesAndAdditionalInfoForm } from "./components/FilesAndAdditionalInfoForm";
import { FormProgress } from "./components/FormProgress";
import { ReportsListPage } from "./components/ReportsListPage";
import { Button } from "./components/ui/button";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { set } from "react-hook-form";

export interface FormData {
  // Patient Information
  patientName: string;
  patientGender: string;
  patientAge: string;
  patientBirthDate: Date | undefined;
  patientWeight: string;
  primaryDiagnosis: string;
  comorbidities: string;

  // Doctor Information
  doctorName: string;
  doctorPosition: string;
  doctorSpecialty: string;
  medicalInstitution: string;
  doctorPhone: string;
  doctorEmail: string;

  // Medication Information
  tradeName: string;
  innName: string;
  dosageForm: string;
  dosage: string;
  dosageUnit: string;
  frequency: string;
  administrationRoute: string;
  startDate: Date | undefined;
  endDate: Date | undefined;
  prescriptionReason: string;
  batchNumber: string;
  manufacturer: string;

  // Adverse Effect Information
  effectDate: Date | undefined;
  effectTime: string;
  effectDescription: string;
  effectLocalization: string;
  severity: string;
  severityCriteria: string;
  actionsTaken: string[];
  treatmentDescription: string;
  outcome: string;
  outcomeDate: Date | undefined;
  previousReactions: string;
  previousReactionsDescription: string;
  causalityAssessment: string;
  causalityFactors: string;

  // Files and Additional Info
  files: File[];
  fileDescriptions: { [key: string]: string };
  additionalInfo: string;
}

const steps = [
  { id: 1, title: "Информация о пациенте" },
  { id: 2, title: "Информация о враче" },
  { id: 3, title: "Информация о препарате" },
  { id: 4, title: "Информация о побочном эффекте" },
  { id: 5, title: "Файлы" },
];

export default function App() {
  const [view, setView] = useState<"list" | "form">("list");
  const [currentStep, setCurrentStep] = useState(1);
  const [ skippedSteps, setSkippedSteps ] = useState<Set<number>>(new Set());
  const [formData, setFormData] = useState<FormData>({
    patientName: "",
    patientGender: "",
    patientAge: "",
    patientBirthDate: undefined,
    patientWeight: "",
    primaryDiagnosis: "",
    comorbidities: "",
    doctorName: "",
    doctorPosition: "",
    doctorSpecialty: "",
    medicalInstitution: "",
    doctorPhone: "",
    doctorEmail: "",
    tradeName: "",
    innName: "",
    dosageForm: "",
    dosage: "",
    dosageUnit: "мг",
    frequency: "",
    administrationRoute: "",
    startDate: undefined,
    endDate: undefined,
    prescriptionReason: "",
    batchNumber: "",
    manufacturer: "",
    effectDate: undefined,
    effectTime: "",
    effectDescription: "",
    effectLocalization: "",
    severity: "",
    severityCriteria: "",
    actionsTaken: [],
    treatmentDescription: "",
    outcome: "",
    outcomeDate: undefined,
    previousReactions: "",
    previousReactionsDescription: "",
    causalityAssessment: "",
    causalityFactors: "",
    files: [],
    fileDescriptions: {},
    additionalInfo: "",
  });

  const handleNext = (data: Partial<FormData>) => {
    setFormData({ ...formData, ...data });
    setCurrentStep(currentStep + 1);
  };

  const handleBack = () => {
    if (currentStep === steps.length && skippedSteps.size > 0) {
      setCurrentStep(1);
      setSkippedSteps(new Set());
    } else {
      setCurrentStep((prev) => Math.max(1, prev - 1));
    }
  };

  const handleSkipToFiles = () => {
  setCurrentStep(5);
};

  const handleSubmit = (data: Partial<FormData>) => {
    const finalData = { ...formData, ...data };
    setFormData(finalData);
    
    console.log("Отправка данных о побочном эффекте:", finalData);
    
    toast.success("Отчет успешно отправлен!", {
      description: "Спасибо за вашу информацию. Ваш отчет будет рассмотрен специалистами по фармаконадзору.",
    });

    // Reset form and return to list
    setTimeout(() => {
      setCurrentStep(1);
      setFormData({
        patientName: "",
        patientGender: "",
        patientAge: "",
        patientBirthDate: undefined,
        patientWeight: "",
        primaryDiagnosis: "",
        comorbidities: "",
        doctorName: "",
        doctorPosition: "",
        doctorSpecialty: "",
        medicalInstitution: "",
        doctorPhone: "",
        doctorEmail: "",
        tradeName: "",
        innName: "",
        dosageForm: "",
        dosage: "",
        dosageUnit: "мг",
        frequency: "",
        administrationRoute: "",
        startDate: undefined,
        endDate: undefined,
        prescriptionReason: "",
        batchNumber: "",
        manufacturer: "",
        effectDate: undefined,
        effectTime: "",
        effectDescription: "",
        effectLocalization: "",
        severity: "",
        severityCriteria: "",
        actionsTaken: [],
        treatmentDescription: "",
        outcome: "",
        outcomeDate: undefined,
        previousReactions: "",
        previousReactionsDescription: "",
        causalityAssessment: "",
        causalityFactors: "",
        files: [],
        fileDescriptions: {},
        additionalInfo: "",
      });
      setView("list");
    }, 2000);
  };

  const handleNewReport = () => {
    setView("form");
    setCurrentStep(1);
  };

  if (view === "list") {
    return <ReportsListPage onNewReport={handleNewReport} />;
  }

  const skipToLast = () => {
    const newSkipped = new Set<number>();
    for (let i = currentStep; i < steps.length; i++) {
      newSkipped.add(i);
    }
    setSkippedSteps(new Set([...skippedSteps, ...newSkipped]));
    setCurrentStep(steps.length);
  }

  const goBackStep = () => {
    setCurrentStep(1);
    setSkippedSteps(new Set());
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 bg-gradient_main">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => setView("list")}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Вернуться к списку
          </Button>
        </div>
        <div className="mb-6 text-center">
          <h1 className="mb-4">Сообщить о побочном эффекте</h1>
          <p className="text-gray-600 max-w-3xl mx-auto">
            Уважаемые врачи! Пожалуйста, заполните форму ниже и прикрепите файлы
            (медицинские заключения, результаты анализов и т.д.), если это
            необходимо. Ваша информация поможет нам выявить и предотвратить
            нежелательные реакции на лекарственные препараты.
          </p>
        </div>

        <FormProgress 
        steps={steps}
        currentStep={currentStep}
        skippedSteps={skippedSteps}
        />

        <div className="bg-white rounded-lg shadow-lg p-8 mt-8">
          {currentStep === 1 && (
            <PatientInfoForm
              data={formData}
              onNext={handleNext}
              onSkipToFiles={skipToLast}
            />
          )}

          {currentStep === 2 && (
            <DoctorInfoForm
              data={formData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 3 && (
            <MedicationInfoForm
              data={formData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 4 && (
            <AdverseEffectInfoForm
              data={formData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 5 && (
            <FilesAndAdditionalInfoForm
              data={formData}
              onSubmit={handleSubmit}
              onBack={handleBack}
              onGoBackToFirst={goBackStep}
            />
          )}
        </div>
      </div>
    </div>
  );
}
