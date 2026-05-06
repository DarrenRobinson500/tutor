import React from 'react';

interface StepIndicatorProps {
  currentStep: number;
  steps: string[];
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep, steps }) => {
  return (
    <div className="rtf-step-indicator">
      {steps.map((label, i) => {
        const num = i + 1;
        const isComplete = num < currentStep;
        const isActive = num === currentStep;
        return (
          <React.Fragment key={num}>
            <div className="rtf-step-item">
              <div className={`rtf-step-circle${isComplete ? ' complete' : ''}${isActive ? ' active' : ''}`}>
                {isComplete ? '✓' : num}
              </div>
              <span className="rtf-step-label">{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`rtf-step-line${isComplete ? ' complete' : ''}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default StepIndicator;
