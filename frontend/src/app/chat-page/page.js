'use client'
import parse from 'html-react-parser';
import Image from "next/image";
import { isElementEmpty } from "@/utils/isElementEmpty";
import styles from "./page.module.css";
import { useRef, useState, useEffect } from "react";
import { useAtom, useAtomValue } from 'jotai';
import { form } from '@/atoms/formAtom';



const ChatPage = () => {  

  let chatTextAreaRef = useRef(null);

  const [formPackage, setForm] = useAtom(form);
  const [currentQuery, setCurrentQuery] = useState("");
  const [showEmptyError, setShowEmptyError] = useState(false);
  const [aiResponse, setAIResponse] = useState(null);
  const [submitted, setSubmittedFlag] = useState(false);
  const [useDetailedAnswer, setDetailedAnswer] = useState(false);
  const [useButtonAnswerType, setButtonAnswerType] = useState("Show Detailed Answer");
  const [shownAnswer, setShownAnswer ] = useState("");
  
  // TODO: Refactor to get rid of problem message
  useEffect(() => {
    handleSubmit();
    displayQuery();
    setSubmittedFlag(true);
  }, []);

  useEffect(() => {
    
    if(aiResponse) {
      const simpleResponse = aiResponse.laymans_answer; // No by-law references
      const advancedResponse = aiResponse.answer; // With by-law references
      const filtered = aiResponse.filtered_answer; // Active bylaws only
      
      // Six combinations
      // active and simple
      // active and advanced
      // inactive and simple
      // inactive and advanced
      // all and simple
      // all and advanced
          
      useDetailedAnswer ? setShownAnswer(advancedResponse) : setShownAnswer(simpleResponse);
    }
    
    
    

  },[aiResponse, useDetailedAnswer])

  const displayResponse = () => {          
    return (
      <div className={styles.messagesWrapper}>
        <div className={styles.systemMessage}>                      
          <div>{parse(shownAnswer)}</div>                       
          <button onClick={() => handleAnswerSwitch()} className={styles.buttonSwitch}>{useButtonAnswerType}</button>
        </div>
      </div>  
    );
  }

  
  const handleClick = (e) => {
    if(isElementEmpty(chatTextAreaRef.current)) {        
      e.preventDefault(); 
      setShowEmptyError(true);
    } else { 
      setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
      setShowEmptyError(false);
      handleSubmit();
      setCurrentQuery("");
    }
  }
  
  const handleEnter = (e) => {                      
    if (e.key === "Enter" && !e.shiftKey) {                   
      e.preventDefault(); 
      if(isElementEmpty(chatTextAreaRef.current)) {        
        setShowEmptyError(true);
      }
      else {                                   
        setSubmittedFlag(true);
        setForm({...formPackage, query: chatTextAreaRef.current.value || ""});                                          
        setShowEmptyError(false);        
        setCurrentQuery(chatTextAreaRef.current.value);
        handleSubmit();           
        chatTextAreaRef.current.value = ""
      }      
    }                                                         

    console.log(formPackage.query);
  }

  const handleChange = () => {         
    setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
    setShowEmptyError(false);
  }


  // Queries the API when user submits the field
  const handleSubmit = async () => {
    if(formPackage.query !== "") {
      try {
        const response = await fetch('api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json'},
          body: JSON.stringify({query: formPackage.query, bylaw_status: formPackage.bylaw_status})
        });

        if (!response.ok) throw new Error('Failed to submit');

        const data = await response.json();
        setAIResponse(data.result);
        setShownAnswer(data.result.laymans_answer)
        console.log("Response from API:", data);
      
      } catch (error) {
        console.error("Submission error:", error);
      }
    }
  }
  
  const displayQuery = () => {              
    return (
      <div className={styles.messagesWrapper}>                          
          <div className={styles.userMessage}>
            {currentQuery}                  
          </div>
      </div>
    );    
  }

  const handleAnswerSwitch = () => {
    setDetailedAnswer(prev => {
      const newState = !prev;
      setButtonAnswerType(newState ? "Show Simple Answer" : "Show Detailed Answer");
      return newState;
    });
};


  return (    
    <>
      <>
        <div className={styles.chatMessagesContainer}>            
          
          {submitted && displayQuery()}
          {displayResponse()}

        </div>        
      </>    
        
      <div className={styles.textareaChatContainer}>        
        <div>
            <div className={styles.textareaChatWrapper}>
                <textarea 
                  ref={chatTextAreaRef} 
                  className={styles.textareaChat} 
                  placeholder="Ask Anything"
                  onKeyDown={handleEnter}
                  onChange={handleChange}
                  type={"text"}
                  rows={1}                                    
                />
            </div>
            <div className={styles.overlayImage}>
              <Image onClick={handleClick} className="clickable-image" src="/assets/images/Send-button.svg" height={30} width={30} alt="send button image"/>            
            </div>
            {showEmptyError && (
                <p className={styles.errorText}>Please fill out this field</p> 
            )}
        </div>
      </div>                      
    </>
  );
}

export default ChatPage;