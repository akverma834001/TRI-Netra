import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  text?: string;
}

export const DisclaimerBanner: React.FC<Props> = ({ text }) => {
  return (
    <div className="disclaimer-banner">
      <AlertTriangle size={14} />
      <span>{text || "Research / Demonstration Prototype — Not a Clinically Validated Diagnostic Device"}</span>
    </div>
  );
};
