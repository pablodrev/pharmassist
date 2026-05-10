export interface Report {
  id: string;
  status: "incoming" | "clarification" | "analysis";
  patientName: string;
  patientId: string;
  medicationName: string;
  adverseEffect: string;
  dateReceived: Date;
  aiNotes: string[];
  completeness: {
    patientInfo: boolean;
    doctorInfo: boolean;
    medicationStartDate: boolean;
    medicationEndDate: boolean;
    medicationBatch: boolean;
    effectDate: boolean;
    effectDescription: boolean;
    severity: boolean;
    outcome: boolean;
  };
  causalityAssessment?: string;
  severity?: string;
  clinicalSignificance?: string;
  definitionForesight?: string;
  fullData: any;
  confirmed?: boolean;
  description?: string;
}
