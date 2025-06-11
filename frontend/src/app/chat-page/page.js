'use client'
import parse from 'html-react-parser';
import Image from "next/image";
import { isElementEmpty } from "@/utils/isElementEmpty";
import styles from "./page.module.css";
import { useRef, useState, useEffect } from "react";
import { useAtom } from 'jotai';
import { form } from '@/atoms/formAtom';



const ChatPage = () => {  

  let chatTextAreaRef = useRef(null);

  const [formPackage, setForm] = useAtom(form);
  const [currentQuery, setCurrentQuery] = useState("");
  const [showEmptyError, setShowEmptyError] = useState(false);
  const [aiResponse, setAIResponse] = useState(null);
  const [submitted, setSubmittedFlag] = useState(false);
  
  // TODO: Refactor to get rid of problem message
  useEffect(() => {
    handleSubmit();
    displayQuery();
    setSubmittedFlag(true);
  }, []);
  
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
        setCurrentQuery("");
        handleSubmit();           
      }      
    }                                                         

    console.log(formPackage.query);
  }

  const handleChange = () => {         
    const userQuery = chatTextAreaRef.current.value;
    setCurrentQuery(userQuery);
    setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
    setShowEmptyError(false);
  }


  const handleSubmit = async () => {
    try {
      const response = await fetch('api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json'},
        body: JSON.stringify({query: formPackage.query, bylaw_status: formPackage.bylaw_status})
      });

      if (!response.ok) throw new Error('Failed to submit');

      const data = await response.json();
      setAIResponse(data.result);
      console.log("Response from API:", data);
    
    } catch (error) {
      console.error("Submission error:", error);
    }
  }
  
  const displayQuery = () => {      
    return (
      <div className={styles.messagesWrapper}>                          
          <div className={styles.userMessage}>
            {formPackage.query}                  
          </div>
      </div>
    );
  }

  const displayResponse = () => {      
    
    if(!aiResponse) return null;
    
    const simpleResponse = aiResponse.laymans_answer;
    // const advancedResponse = aiResponse.answer;
    // const filtered = aiResponse.filtered_answer;    
    return (
      <div className={styles.messagesWrapper}>
        <div className={styles.systemMessage}>                      
          <div>{parse(simpleResponse)}</div>                       
        </div>
      </div>  
    );
  }

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
                  value={currentQuery || ""}
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