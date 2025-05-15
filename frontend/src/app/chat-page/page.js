import Image from "next/image";
import styles from "./page.module.css";

const ChatPage = () => {
  return (    
    <div>
      <div className={styles.chatMessagesContainer}>
        <div className={styles.messages}>
          <div className={styles.userMessage}>
            <p className={styles.message}>Can my dog poop on someone elses lawn?</p>
          </div>
          <div className={styles.systemMessage}>
          <h4>Dog Excrement on Private Property</h4>

          
            You must immediately remove and properly dispose of any excrement 
            left by your dog on public or private property that is not your 
            own. You must also remove and properly dispose of excrement on 
            your own property in a timely manner.
          
          </div>
        </div>
      </div>
      
      <div>
        <div className={styles.textareaChatContainer}>        
          <textarea className={styles.textareaChat} placeholder="Ask Anything"></textarea>
        </div>              
      </div>          
    </div>
  );
}

export default ChatPage;