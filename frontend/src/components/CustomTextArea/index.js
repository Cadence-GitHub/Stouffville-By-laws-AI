'use client'
import { useRef, useEffect, useState } from "react";
import { useAtom, useAtomValue } from 'jotai';
import { form, submitSignalAtom } from "@/atoms/formAtom.js";
import styles from "./CustomTextArea.module.css"

const CustomTextArea = ({placeholder, field, ...props}) => {
    const textAreaRef = useRef(null);

    const [formPackage, setForm] = useAtom(form);
    const [showEmptyError, setShowEmptyError] = useState(false);
    const [submitSignal, setSubmitSignal] = useAtom(submitSignalAtom);
    const [aiSuggestions, setAiSuggestions] = useState([]);
    
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
            
            console.log("in customTextArea handlEnter");
            if(e.target.value === "") {

                e.preventDefault(); 
                setShowEmptyError(true);
                textAreaRef.current?.focus();    
                console.log("textarea is \"\"");

            } else { 

                e.preventDefault();                            
                setForm({ ...formPackage, [field]: formPackage[field] || ""});                
                console.log("textarea is not \"\"");                            
                e.target.form?.requestSubmit();      
            }                        
        }                         
    }


    // const handleChange = async (e) => {                    
    //     try {            
    //         setForm({ ...formPackage, [field]: e.target?.value || "" });
    //         if (e.target.value.trim() !== "") {
    //             setShowEmptyError(false);

    //         }

    //         const response = await fetch('api/autocomplete', {
    //             method: 'POST',
    //             headers: { 'Content-Type': 'application/json'},
    //             body: JSON.stringify({query: formPackage.query})
    //         });

    //         if (!response.ok) throw new Error('Failed to submit');

    //         const data = await response.json();
    //         setAiSuggestions(data.result);
    //         console.log("Response from autocomplete API:", data);        
    //     } catch (error) {
    //         console.error("Submission error:", error);
    //     }

    // }

    const handleChange = async (e) => {
        try {
            const updatedForm = { ...formPackage, [field]: e.target?.value || "" };
            setForm(updatedForm);

            if (e.target.value.trim() !== "") {
            setShowEmptyError(false);
            }

            const response = await fetch('/api/autocomplete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: updatedForm.query })
            });

            if (!response.ok) throw new Error('Failed to fetch suggestions');

            const data = await response.json();
            setAiSuggestions(data.result.suggestions); // Use `result` instead of `suggestions`
            console.log("Response from autocomplete API:", data);

        } catch (error) {
            console.error("Autocomplete error:", error);
        }
    };


    // Handles the behaviour of checking whether or not it has a non-empty value
    useEffect(() => {
        if(!submitSignal) {
            return; // Doesnt do any checking if user has not submmited
        }

        if(textAreaRef.current.value !== "") {
            console.log("textarea has value");
            setShowEmptyError(false);
        } else { 
            console.log("textarea is missing value");
            setShowEmptyError(true);
        }
    }, [submitSignal]);


    // Handles getting the suggestions
    useEffect(() => {

    }, []);

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

            
            
            <div className={styles.suggestionDropDown}>
                {aiSuggestions.map((suggestion, index) => (
                    <div key={index} onClick={() => handleSelect(suggestion)} className={styles.dropdown_item}>
                        {suggestion}
                    </div>
                ))}
            </div>
            {/* {aiSuggestions.length > 0 && (
            )} */}
            
            
            {/* {aiSuggestions && (
                <div className={styles.suggestionDropDown}>
                    {aiSuggestions.map((suggestion) => (
                        <div key={suggestion} onClick={() => handleSelect(suggestion)} className={styles.dropdown_item}>                  
                            {suggestion}
                        </div>
                    ))}
                </div>
            )} */}

            {showEmptyError && (
                <p className={styles.errorText}>Please fill out this field</p> 
            )}
        </div>
    );
}

export default CustomTextArea;
