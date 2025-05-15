'use client'
import { useRouter } from "next/navigation";
import DynamicFormTemplate from "@/components/DynamicFormTemplate";

export default function Home() {
  
  const router = useRouter();
  
  return (
    <div className="contentContainer">
      <div>        
        <p>What would you like to know?</p>        
        {/* TODO: Button routes to a FAQ page */}
        <button className="buttonRoute" onClick={() => router.push('/faq-page')}>FAQ</button>          
        <DynamicFormTemplate/>
      </div>
    </div>
  );
}