import { useState } from "react";
import { PatientInfoForm } from "./components/PatientInfoForm";
import { DoctorInfoForm } from "./components/DoctorInfoForm";
import { MedicationInfoForm } from "./components/MedicationInfoForm";
import { AdverseEffectInfoForm } from "./components/AdverseEffectInfoForm";
import { FilesAndAdditionalInfoForm } from "./components/FilesAndAdditionalInfoForm";
import { FormProgress } from "./components/FormProgress";
import { ReportsListPage } from "./components/ReportsListPage";
import { LoginPage } from "./components/LoginPage";
import { RegisterPage } from "./components/RegisterPage";
import { NewReportChoice } from "./components/NewReportChoice";
import { FreeTextReportForm } from "./components/FreeTextReportForm";
import { SpecialistReviewPage } from "./components/SpecialistReviewPage";
import { Button } from "./components/ui/button";
import { toast } from "sonner";
import { ArrowLeft, LogOut } from "lucide-react";
import { useAuth } from "./auth/AuthContext";
import { apiClient } from "./api/client";
import { mapFormDataToCreateReport } from "./api/reportMapper";

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

const EMPTY_FORM: FormData = {
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
};

export default function App() {
  const { user, loading, logout } = useAuth();
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const [view, setView] = useState<
    "list" | "choice" | "form" | "freetext" | "specialist-review"
  >("list");
  const [openReportId, setOpenReportId] = useState<string | null>(null);
  const [listRefreshKey, setListRefreshKey] = useState(0);
  const [submitting, setSubmitting] = useState(false);
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

  const resetForm = () => {
    setCurrentStep(1);
    setSkippedSteps(new Set());
    setFormData(EMPTY_FORM);
  };

  const handleSubmit = async (data: Partial<FormData>) => {
    const finalData = { ...formData, ...data };
    setFormData(finalData);

    if (!finalData.effectDescription || finalData.effectDescription.trim().length === 0) {
      toast.error("Заполните описание побочного эффекта");
      return;
    }

    setSubmitting(true);
    try {
      const body = mapFormDataToCreateReport(finalData);
      const { error } = await apiClient.POST("/api/v1/reports/from-form", {
        body,
      });
      if (error) {
        const msg =
          (error as { detail?: unknown }).detail &&
          typeof (error as { detail?: unknown }).detail === "string"
            ? ((error as { detail: string }).detail)
            : "Не удалось отправить сообщение";
        throw new Error(msg);
      }
      toast.success("Сообщение принято", {
        description:
          "AI начал анализ — результат появится в списке через ~15 секунд.",
      });
      resetForm();
      setListRefreshKey((k) => k + 1);
      setView("list");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ошибка отправки");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNewReport = () => {
    resetForm();
    setView("choice");
  };

  const handleFreeTextSubmitted = () => {
    setListRefreshKey((k) => k + 1);
    setView("list");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Загрузка...
      </div>
    );
  }

  if (!user) {
    return authView === "login" ? (
      <LoginPage onSwitchToRegister={() => setAuthView("register")} />
    ) : (
      <RegisterPage onSwitchToLogin={() => setAuthView("login")} />
    );
  }

  if (user.role === "specialist") {
    if (view === "specialist-review" && openReportId) {
      return (
        <SpecialistReviewPage
          reportId={openReportId}
          onBack={() => {
            setOpenReportId(null);
            setView("list");
            setListRefreshKey((k) => k + 1);
          }}
          onFinalized={() => {
            setOpenReportId(null);
            setView("list");
            setListRefreshKey((k) => k + 1);
          }}
        />
      );
    }
    return (
      <div>
        <div className="bg-white border-b px-4 py-2 flex justify-between items-center">
          <span className="text-sm text-gray-600">
            {user.full_name} ({user.email}) — специалист
          </span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="w-4 h-4 mr-2" /> Выйти
          </Button>
        </div>
        <ReportsListPage
          refreshKey={listRefreshKey}
          showNewButton={false}
          title="Очередь специалиста"
          onOpenReport={(id) => {
            setOpenReportId(id);
            setView("specialist-review");
          }}
        />
      </div>
    );
  }

  if (view === "list") {
    return (
      <div>
        <div className="bg-white border-b px-4 py-2 flex justify-between items-center">
          <span className="text-sm text-gray-600">
            {user.full_name} ({user.email})
          </span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="w-4 h-4 mr-2" /> Выйти
          </Button>
        </div>
        <ReportsListPage
          refreshKey={listRefreshKey}
          onNewReport={handleNewReport}
        />
      </div>
    );
  }

  if (view === "choice") {
    return (
      <NewReportChoice
        onChooseForm={() => setView("form")}
        onChooseFreeText={() => setView("freetext")}
        onBack={() => setView("list")}
      />
    );
  }

  if (view === "freetext") {
    return (
      <FreeTextReportForm
        onSubmitted={handleFreeTextSubmitted}
        onBack={() => setView("choice")}
      />
    );
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
            onClick={() => setView("choice")}
            className="mb-4"
            disabled={submitting}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Назад
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
