'use client'
import DynamicFormTemplate from "@/components/DynamicFormTemplate";

export default function Home() {
  return (
    <div className="contentContainer">
      <div>        
        <p>What would you like to know?</p>             
        <DynamicFormTemplate/>        
      </div>
    </div>
  );
}