'use client'
import Image from "next/image";
import DynamicForms from "@/components/DynamicForms";
import { useState } from "react";

export default function Home() {
  
  const [chatInitiated, setChatInitiated] = useState(false);
  
  return (
    // setChatInitiated is the flag that will cause the page to re-render with the chatbox ui.
    // We are passing a callback function as a prop when the user clicks on the submit button inside <DynamicForms>
    !chatInitiated ? (<StarterPage startChat={() => setChatInitiated(true)}/>) : (<ChatBox/>)
  );
}

const StarterPage = ({startChat}) => {
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

        <DynamicForms startChat={startChat}/>

      </div>
    </div>
  );
}

const ChatBox = () => {
  return (
    <div className="contentContainer">
      <div className="centerItems">
        <div className="chatBoxContainer"></div>
          <div className="input-wrapper">
            <textarea className="chat-textarea" placeholder="Ask Anything">
            </textarea>
            <button className="submitButtonQuery" style={{right: "35px", bottom: "5px"}}>
              <Image 
                src="/assets/images/Send-button.svg" 
                alt="send button" 
                width={25} 
                height={25}
              />
            </button>
          </div>

      </div>
    </div>
  );
}