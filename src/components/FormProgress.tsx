import { Check, AlertCircle } from "lucide-react";

interface Step {
  id: number;
  title: string;
}

interface FormProgressProps {
  steps: Step[];
  currentStep: number;
  skippedSteps: Set<number>;
}

export function FormProgress({ steps, currentStep, skippedSteps }: FormProgressProps) {
  return (
    <div className="w-full mb-2">
      <div className="flex items-start justify-between">
        {steps.map((step, index) => {
          const isSkipped = skippedSteps.has(step.id);
          const isCompleted = step.id < currentStep && !isSkipped;
          const isCurrent = step.id === currentStep;
          const isFuture = step.id > currentStep;

          let circleClass = "w-10 h-10 rounded-full flex items-center justify-center transition-all";
          let textClass = "mt-2 h-5 text-xs text-center";
          let iconOrNumber;

          if (isCompleted) {
            circleClass += " bg-green-500 text-white";
            textClass += " text-green-600";
            iconOrNumber = <Check className="w-5 h-5" />;
          } else if (isSkipped) {
            circleClass += " bg-red-500 text-white";
            textClass += " text-red-600";
            iconOrNumber = <AlertCircle className="w-5 h-5" />;
          } else if (isCurrent) {
            circleClass += " bg-indigo-600 text-white ring-4 ring-indigo-200";
            textClass += " text-indigo-600";
            iconOrNumber = <span>{step.id}</span>;
          } else if (isFuture) {
            circleClass += " bg-gray-200 text-gray-500";
            textClass += " text-gray-500";
            iconOrNumber = <span>{step.id}</span>;
          }

          return (
            <div key={step.id} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div className={circleClass}>{iconOrNumber}</div>
                <p className={textClass}>{step.title}</p>
              </div>
              {index < steps.length - 1 && (
                <div className="flex-1 h-1 mx-2 mb-8">
                  <div
                    className={`h-full transition-all ${
                      step.id < currentStep
                        ? skippedSteps.has(step.id + 1)
                          ? "bg-red-500"
                          : "bg-green-500"
                        : "bg-gray-200"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}