'use client'
import { useRef, useState } from "react";
import styles from "./CustomTextArea.module.css"

const CustomTextArea = ({placeholder}) => {
    const textAreaRef = useRef(null);

    const resizeOnInput = () => {
        
        let elementRef = textAreaRef.current;
        if (elementRef) {

            elementRef.style.height = '35px';
            let contentHeight = elementRef.scrollHeight;
            const maxHeight = 70;
    
            if(contentHeight <= maxHeight) {
                elementRef.style.height = contentHeight + 'px'; // Set to scroll height
                elementRef.style.overflow = 'hidden';
            }
            else {
                elementRef.style.height = maxHeight + 'px'; // Set to scroll height
                elementRef.style.overflow = 'auto'; // Reset
            }
        }      
    }   

    // This also grabs the text user enetered when they press enter    
    const handleEnter = (e) => {                        
        let userQuery = textAreaRef.current?.value;
        
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();                   
            
            if(userQuery === null || userQuery === "") {
                userQuery = placeholder;
                console.log(userQuery);
            }
            else {
                console.log(userQuery);
            }
        }                  
    }

    return (
        <div className={styles.inputWrapper}>
            <textarea 
                id="useQuery"
                ref={textAreaRef}
                className={styles.textareaInput}
                placeholder={placeholder}   
                rows={1}
                onInput={resizeOnInput}
                onKeyDown={handleEnter}
                >
            </textarea>
        </div>
    );
}

export default CustomTextArea;
