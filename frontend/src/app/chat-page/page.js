'use client'
import Image from "next/image";
import { isElementEmpty } from "@/utils/isElementEmpty";
import styles from "./page.module.css";
import { useRef, useState } from "react";
import { useAtom } from 'jotai';
import { form } from '@/atoms/formAtom';



const ChatPage = () => {  

  let chatTextAreaRef = useRef(null);

  const [formPackage, setForm] = useAtom(form);
  const [currentQuery, setCurrentQuery] = useState("");
  const [showEmptyError, setShowEmptyError] = useState(false);
  
  
  const handleClick = (e) => {
    if(isElementEmpty(chatTextAreaRef.current)) {        
      e.preventDefault(); 
      setShowEmptyError(true);
    } else { 
      setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
      setShowEmptyError(false);
      e.target.form?.requestSubmit();  
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
        setForm({...formPackage, query: chatTextAreaRef.current.value || ""});                                          
        setShowEmptyError(false);        
        setCurrentQuery("");
        e.target.form?.requestSubmit();              
      }      
    }                                                         

    console.log(formPackage.query);
  }

  const handleChange = (e) => {         
    const userQuery = chatTextAreaRef.current.value;
    setCurrentQuery(userQuery);
    setForm({...formPackage, query: chatTextAreaRef.current.value || ""});    
    setShowEmptyError(false);
  }

  return (    
    <>

      <>
        <div className={styles.chatMessagesContainer}>            
          
          <div className={styles.messagesWrapper}>                          
              <div className={styles.userMessage}>
                Can my dog poop on someone elses lawn?                          
              </div>
          </div>
            
          <div className={styles.messagesWrapper}>
            <div className={styles.systemMessage}>            
              <div>
                <b>Dog Excrement on Private Property</b>
              </div>
              <div>              
                You must immediately remove and properly dispose of any excrement 
                left by your dog on public or private property that is not your 
                own. You must also remove and properly dispose of excrement on 
                your own property in a timely manner.                        
              </div>
            </div>
          </div>      

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