'use client'
import { useRef, useEffect, useState } from "react";
import { useAtom } from 'jotai';
import { form } from '@/atoms/formAtom.js';
import styles from "./CustomTextArea.module.css"

const CustomTextArea = ({placeholder, field, ...props}) => {
    const textAreaRef = useRef(null);

    const [formPackage, setForm] = useAtom(form);
    const [showEmptyError, setShowEmptyError] = useState(false); // 1. Track error state
    // const [userQueryInput, setUserInput] = useState('');

    const resizeOnInput = () => {
        
        let elementRef = textAreaRef.current;
        if (elementRef) {
                    
            elementRef.style.height = '35px';
            let contentHeight = elementRef.scrollHeight;
            const maxHeight = 70;
            elementRef.style.overflow = 'hidden';

            if(elementRef.value !== "") {
                        
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
    }   

    const handleEnter = (e) => {                
        if (e.key === "Enter" && !e.shiftKey) {
            
            if(e.target.value === "") {

                e.preventDefault(); 
                setShowEmptyError(true);
                textAreaRef.current?.focus();                

            } else { 

                e.preventDefault();                            
                setForm({ ...formPackage, [field]: formPackage[field] || ""});                
                            
                e.target.form?.requestSubmit();      
            }
            
            
        }                         
    }


    const handleChange = (e) => {    
        
        setForm({ ...formPackage, [field]: e.target?.value || "" });
        if (e.target.value.trim() !== "") {
            setShowEmptyError(false);
        }
    }

    return (
        <div className={styles.inputWrapper}>   
            <textarea 
                className={styles.textareaInput}
                ref={textAreaRef}
                value={formPackage[field] || ""}
                onInput={resizeOnInput}
                onKeyDown={handleEnter}
                onChange={handleChange}
                placeholder={placeholder}   
                type="text" 
                {...props}
                rows={1}                
                >
            </textarea>
            {showEmptyError && (
                <p className={styles.errorText}>Please fill out this field</p> 
            )}
        </div>
    );
}

export default CustomTextArea;
