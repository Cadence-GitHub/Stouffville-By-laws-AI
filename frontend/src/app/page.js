'use client'

import styles from "./page.module.css";
import DynamicInput from "@/components/DynamicInput";

export default function Home() {
  
  return (
    <div className="contentContainer">
      <div className="centerItems">
        
        {/* I wanted a 45px gap between the p and button, hence the hardcoded margins */}
        <p style={{fontWeight: "500", color: "#0060A1", marginBottom: 22.5}}> 
          What would you like to know?
        </p>
        
        {/* TODO: Button routes to a FAQ page */}
        <div style={{margin: 22.5}}>
          <button className="buttonRoute">
            FAQ
          </button>
        </div>

        <DynamicInput/>

      </div>
    </div>
  );
}
