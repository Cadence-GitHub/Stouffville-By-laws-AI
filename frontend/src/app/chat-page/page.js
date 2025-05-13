import Image from "next/image";
import styles from "./page.module.css";

const chatpage = () => {
  return (    
    <div className={styles.textareaChatContainer}>
        <textarea className={styles.textareaChat} placeholder="Ask Anything"></textarea>
    </div>            
  );
}

export default chatpage;