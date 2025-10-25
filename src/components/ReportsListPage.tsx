import { useState, useMemo } from "react";
import { Report } from "../types/report";
import { mockReports } from "../data/mockReports";
import { ReportCard } from "./ReportCard";
import { ReportDetails } from "./ReportDetails";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Button } from "./ui/button";
import { Search, Filter, Plus } from "lucide-react";

interface ReportsListPageProps {
  onNewReport: () => void;
}

export function ReportsListPage({ onNewReport }: ReportsListPageProps) {
  const [reports, setReports] = useState<Report[]>(mockReports);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [medicationFilter, setMedicationFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [activeTab, setActiveTab] = useState<Report["status"]>("incoming");

  const handleStatusChange = (reportId: string, newStatus: Report["status"]) => {
    setReports((prevReports: Report[]) =>
      prevReports.map((report) =>
        report.id === reportId ? { ...report, status: newStatus } : report
      )
    );

    setSelectedReport((prev: Report | null) =>
      prev && prev.id === reportId ? { ...prev, status: newStatus } : prev
    );
  };

  const handleConfirm = (reportId: string) => {
    setReports((prev) =>
      prev.map((r) => (r.id === reportId ? { ...r, confirmed: true } : r))
    );
  };


  // Get unique medications for filter
  const uniqueMedications = useMemo(() => {
    const meds = new Set(reports.map((r) => r.medicationName));
    return Array.from(meds);
  }, [reports]);

  // Filter reports
  const filteredReports = useMemo(() => {
    return reports.filter((report) => {
      // Tab filter
      if (report.status !== activeTab) return false;

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          report.patientName.toLowerCase().includes(query) ||
          report.medicationName.toLowerCase().includes(query) ||
          report.adverseEffect.toLowerCase().includes(query) ||
          report.id.toLowerCase().includes(query);
        if (!matchesSearch) return false;
      }

      // Medication filter
      if (medicationFilter !== "all" && report.medicationName !== medicationFilter) {
        return false;
      }

      // Severity filter
      if (severityFilter !== "all" && report.severity !== severityFilter) {
        return false;
      }

      // Date filter
      if (dateFilter !== "all") {
        const today = new Date();
        const reportDate = report.dateReceived;
        const daysDiff = Math.floor(
          (today.getTime() - reportDate.getTime()) / (1000 * 60 * 60 * 24)
        );

        if (dateFilter === "today" && daysDiff !== 0) return false;
        if (dateFilter === "week" && daysDiff > 7) return false;
        if (dateFilter === "month" && daysDiff > 30) return false;
      }

      return true;
    });
  }, [reports, activeTab, searchQuery, medicationFilter, severityFilter, dateFilter]);

  const getTabCount = (status: Report["status"]) => {
    return reports.filter((r) => r.status === status).length;
  };

  return (
    <div className="min-h-screen bg-gray-50 bg-gradient_main">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 ">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="flex items-center justify-center">
                <img src="src\assets\Frame 4.png" alt="logo" className="h-full w-24" />
                <h1>Управление сообщениями о побочных эффектах</h1>
              </div>
              <p className="text-gray-600 mt-1 mx-2">
                {/* Просмотр и анализ сообщений, обработанных ИИ-ассистентом */}
              </p>
            </div>
            <Button onClick={onNewReport} className="bg-indigo-600 hover:bg-indigo-700">
              <Plus className="w-4 h-4 mr-2" />
              Новое сообщение
            </Button>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Поиск по пациенту, препарату..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select value={medicationFilter} onValueChange={setMedicationFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Все препараты" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все препараты</SelectItem>
                {uniqueMedications.map((med) => (
                  <SelectItem key={med} value={med}>
                    {med}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Все степени тяжести" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все степени тяжести</SelectItem>
                <SelectItem value="mild">Легкая</SelectItem>
                <SelectItem value="moderate">Средняя</SelectItem>
                <SelectItem value="severe">Тяжелая</SelectItem>
                <SelectItem value="life-threatening">Жизнеугрожающая</SelectItem>
              </SelectContent>
            </Select>

            <Select value={dateFilter} onValueChange={setDateFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Все даты" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все даты</SelectItem>
                <SelectItem value="today">Сегодня</SelectItem>
                <SelectItem value="week">За неделю</SelectItem>
                <SelectItem value="month">За месяц</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as Report["status"])}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="incoming">
                Входящие ({getTabCount("incoming")})
              </TabsTrigger>
              <TabsTrigger value="clarification">
                На уточнении ({getTabCount("clarification")})
              </TabsTrigger>
              <TabsTrigger value="analysis">
                Анализ ({getTabCount("analysis")})
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="space-y-4">
          {filteredReports.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Сообщений не найдено</p>
            </div>
          ) : (
            filteredReports.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                onClick={() => setSelectedReport(report)}
              />
            ))
          )}
        </div>
      </div>

      {selectedReport && (
        <ReportDetails
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
          onStatusChange={handleStatusChange}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  );
}
