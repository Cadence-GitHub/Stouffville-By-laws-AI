'use client'
import parse from 'html-react-parser';
import Image from "next/image";
import { useRouter } from "next/navigation";
import { isElementEmpty } from "@/utils/isElementEmpty";
import styles from "./page.module.css";
import { useRef, useState, useEffect } from "react";
import { useAtom } from 'jotai';
import { formAtom } from "@/atoms/formAtom.js";

const ChatPage = () => {  
const router = useRouter();
  let chatTextAreaRef = useRef(null);

  const [formPackage, setForm] = useAtom(formAtom);

  const [currentQuery, setCurrentQuery] = useState("");
  const [showEmptyError, setShowEmptyError] = useState(false);
  const [aiResponse, setAIResponse] = useState({});
  const [submitted, setSubmittedFlag] = useState(false);
  const [useDetailedAnswer, setDetailedAnswer] = useState(false);
  const [useButtonAnswerType, setButtonAnswerType] = useState("Show Detailed Answer");
  const [shownAnswer, setShownAnswer] = useState(null);
  
  useEffect(() => {
    setSubmittedFlag(true);
    setCurrentQuery(formPackage.query);
    displayQuery();    
    handleSubmit();
  }, []);

  
  useEffect(() => {
    setButtonAnswerType(useDetailedAnswer ? "Show Simple Answer" : "Show Detailed Answer");
  }, [useDetailedAnswer]);
  
  const handleAnswerSwitch = () => {
    const isCurrentlyDetailed = useDetailedAnswer; // snapshot of current state

    // First: set the new answer (based on what the current state is)
    if (isCurrentlyDetailed) {
      setShownAnswer(aiResponse.laymans_answer);
    } else {
      setShownAnswer(aiResponse.answer);
    }

    // Then toggle the state
    setDetailedAnswer(prev => !prev);
    // displayResponse();
  };


  const handleClick = (e) => {
    if(isElementEmpty(chatTextAreaRef.current)) {        
      e.preventDefault(); 
      setShowEmptyError(true);
    } else { 
      setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
      setShowEmptyError(false);
      setSignalAtom(true);
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
        displayResponse();
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
    try {                  
      const response = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: formPackage.query, status: formPackage.bylaw_status })
      });

      if (!response.ok) throw new Error('Failed to query ASK api');
      
      const data = await response.json();
      if(data) {                
        setAIResponse(data.result);
      }

      console.log("Response from ask API:", data);                         
            
    } catch (error) {
      console.error("Ask API error:", error);
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

  // Has behaviour set to open the embedded <a> links from filteredResponse in a new tab
  // sets target and rel to a set value to prevent tabnabbing  
  useEffect(() => {            
    if(formPackage.laymans_answer === true) {
      setShownAnswer(aiResponse.laymans_answer)
    } else {
      setShownAnswer(aiResponse.filtered_answer)
    }                                                
  }, [aiResponse, formPackage.laymans_answer]);
  
  const displayResponse = () => {                 
    
    console.log("shownAnswer:", shownAnswer, typeof shownAnswer);
    if (typeof shownAnswer !== "string" || shownAnswer.trim() === "") {
      return null;
    }
    
    return (
      <div className={styles.messagesWrapper}>
        <div className={styles.systemMessage}>                      
          <div>
            {parse(shownAnswer, {
              replace: (domNode) => {
                // Handle <bylaw_url>
                if (domNode.name === "bylaw_url" && domNode.children?.[0]?.data) {
                  const bylawText = domNode.children[0].data;
                  const bylawCode = bylawText.match(/\d{4}-\d{3}/)?.[0] ?? "unknown";
                  return (
                    <a
                      href={`/static/bylawViewer.html?bylaw=${bylawCode}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {bylawText}
                    </a>
                  );
                }

                // Handle <filtered_response>
                if (domNode.name === "filtered_response" && domNode.children?.[0]?.data) {
                  return (
                    <span className="filtered-response">
                      {domNode.children[0].data}
                    </span>
                  );
                }

                return undefined; // fallback to default behavior
              }
            })}          
          <button onClick={() => handleAnswerSwitch()} className={styles.buttonSwitch}>{useButtonAnswerType}</button>
          </div>            
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
        
      <div style={{textAlign: "center"}}>
          <button className="buttonSubmit" onClick={() => router.push('/')}>Ask another question</button>            
      </div>
          
      {/* UNSED UNTIL FURTHER NOTICE */}
      {/* <div style={{display: "none"}} className={styles.textareaChatContainer}>        
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
      </div>                         */}
    </>
  );
}

export default ChatPage;