'use client'
import Image from "next/image";
import styles from "./page.module.css";



const ChatPage = () => {  

  const handleSubmit = (e) => {
      e.preventDefault();
      
      // 

  }

  return (    
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

      
        
        
      <div className={styles.textareaChatContainer}>        
        <div>
            <div className={styles.textareaChatWrapper}>
                <textarea className={styles.textareaChat} placeholder="Ask Anything"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      handleSubmit();
                    }
                  }}
                />
            </div>
            <div className={styles.overlayImage}>
              <Image onClick={() => handleSubmit()} className="clickable-image" src="/assets/images/Send-button.svg" height={30} width={30} alt="send button image"/>            
            </div>
        </div>
      </div>                      
    </>
  );
}

export default ChatPage;