import type { FormData as ReportFormData } from "../App";
import type { components } from "./schema";

type CreateReportFromFormRequest =
  components["schemas"]["CreateReportFromFormRequest"];
type Severity = components["schemas"]["SeverityLevel"];

const VALID_SEVERITIES: Severity[] = [
  "mild",
  "moderate",
  "severe",
  "life-threatening",
];

const isSeverity = (v: string): v is Severity =>
  (VALID_SEVERITIES as string[]).includes(v);

const toIso = (d: Date | undefined): string | null =>
  d ? d.toISOString().slice(0, 10) : null;

const orNull = (s: string | undefined | null): string | null => {
  if (!s) return null;
  const t = s.trim();
  return t.length === 0 ? null : t;
};

/**
 * Maps the rich App.tsx FormData (~60 fields) onto the narrower
 * CreateReportFromFormRequest the backend exposes (~25 fields).
 *
 * Поля, которым нет места в схеме, склеиваем в additional_info.additional_info,
 * чтобы AI мог их подхватить при анализе.
 */
export function mapFormDataToCreateReport(
  data: ReportFormData,
): CreateReportFromFormRequest {
  const dose =
    [data.dosage, data.dosageUnit].filter(Boolean).join(" ").trim() || null;

  const severity =
    data.severity && isSeverity(data.severity) ? data.severity : null;

  const extraNotes: string[] = [];
  if (data.effectTime) extraNotes.push(`Время появления: ${data.effectTime}`);
  if (data.effectLocalization)
    extraNotes.push(`Локализация: ${data.effectLocalization}`);
  if (data.severityCriteria)
    extraNotes.push(`Критерии тяжести: ${data.severityCriteria}`);
  if (data.actionsTaken && data.actionsTaken.length > 0)
    extraNotes.push(`Принятые меры: ${data.actionsTaken.join(", ")}`);
  if (data.treatmentDescription)
    extraNotes.push(`Лечение: ${data.treatmentDescription}`);
  if (data.outcomeDate)
    extraNotes.push(`Дата исхода: ${toIso(data.outcomeDate)}`);
  if (data.previousReactions)
    extraNotes.push(`Предыдущие реакции: ${data.previousReactions}`);
  if (data.previousReactionsDescription)
    extraNotes.push(
      `Описание предыдущих реакций: ${data.previousReactionsDescription}`,
    );
  if (data.causalityFactors)
    extraNotes.push(`Факторы ПСС: ${data.causalityFactors}`);
  if (data.batchNumber) extraNotes.push(`Номер серии: ${data.batchNumber}`);
  if (data.doctorPosition) extraNotes.push(`Должность врача: ${data.doctorPosition}`);
  if (data.doctorPhone) extraNotes.push(`Телефон врача: ${data.doctorPhone}`);
  if (data.patientBirthDate)
    extraNotes.push(`Дата рождения пациента: ${toIso(data.patientBirthDate)}`);

  const additionalInfo = [orNull(data.additionalInfo), ...extraNotes]
    .filter(Boolean)
    .join("\n");

  return {
    patient: {
      name: orNull(data.patientName),
      age: orNull(data.patientAge),
      sex: orNull(data.patientGender),
      weight: orNull(data.patientWeight),
      diagnosis: orNull(data.primaryDiagnosis),
      comorbidities: orNull(data.comorbidities),
    },
    doctor: {
      name: orNull(data.doctorName),
      specialty: orNull(data.doctorSpecialty),
      organization: orNull(data.medicalInstitution),
      email: orNull(data.doctorEmail),
    },
    medication: {
      trade_name: orNull(data.tradeName),
      inn: orNull(data.innName),
      dose,
      route: orNull(data.administrationRoute),
      start_date: toIso(data.startDate),
      end_date: toIso(data.endDate),
      indication: orNull(data.prescriptionReason),
      manufacturer: orNull(data.manufacturer),
    },
    adverse_effect: {
      date: toIso(data.effectDate),
      description: orNull(data.effectDescription) ?? "",
      severity,
      is_serious: severity === "severe" || severity === "life-threatening",
      outcome: orNull(data.outcome),
      causality_assessment: orNull(data.causalityAssessment),
    },
    additional_info: {
      additional_info: additionalInfo.length > 0 ? additionalInfo : null,
    },
  };
}
