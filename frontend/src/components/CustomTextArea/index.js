'use client'
import { useRef } from "react";
import { useAtom } from 'jotai';
import { formAtom } from '@/atoms/formAtoms';
import styles from "./CustomTextArea.module.css"

const CustomTextArea = ({placeholder, field, ...props}) => {
    const textAreaRef = useRef(null);

    const [form, setForm] = useAtom(formAtom);

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

    const handleEnter = (e) => {                
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();    
            
            const userQuery = e.target?.value || placeholder;
            setForm({ ...form, [field]: userQuery });         
        }                         
    }

    const handleChange = (e) => {
        setForm({ ...form, [field]: e.target?.value });
    }

    return (
        <div className={styles.inputWrapper}>
            <textarea 
                className={styles.textareaInput}
                ref={textAreaRef}
                value={form[field] || ''}
                onInput={resizeOnInput}
                onKeyDown={handleEnter}
                onChange={handleChange}
                placeholder={placeholder}   
                type="text" 
                {...props}
                rows={1}                
                >
            </textarea>
        </div>
    );
}

export default CustomTextArea;
