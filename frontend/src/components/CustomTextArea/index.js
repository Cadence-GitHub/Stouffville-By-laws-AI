'use client'
import { useRef, useEffect, useState } from "react";
import { useAtom, useAtomValue } from 'jotai';
import { form, submitSignalAtom } from "@/atoms/formAtom.js";
import styles from "./CustomTextArea.module.css"

const CustomTextArea = ({placeholder, field, ...props}) => {
    const textAreaRef = useRef(null);
    const [isOpen, setIsOpen] = useState(false);
    const [formPackage, setForm] = useAtom(form);
    const [showEmptyError, setShowEmptyError] = useState(false);
    const [submitSignal, setSubmitSignal] = useAtom(submitSignalAtom);
    const [aiSuggestions, setAiSuggestions] = useState([]);
    
    const resizeOnInput = () => {
        const elementRef = textAreaRef.current;

        if (elementRef) {
            const maxHeight = 70;
            elementRef.style.height = 'auto'; // Reset to natural height
            elementRef.style.overflow = 'hidden'; // Default

            const scrollHeight = elementRef.scrollHeight;

            if (elementRef.value.trim() !== "") {
                const newHeight = Math.min(scrollHeight, maxHeight);
                elementRef.style.height = `${newHeight}px`;

                if (scrollHeight > maxHeight) {
                    elementRef.style.overflow = 'auto';
                }
            }
        }
    };

    // Checks if input is empty on enter; shows error message below the input field 
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

    // fetches auto complete suggestions and controls when the list of suggestions show
    const handleChange = async (e) => {
        try {
            const updatedForm = { ...formPackage, [field]: e.target?.value || "" };
            setForm(updatedForm);
            setShowEmptyError(false);

            const response = await fetch('/api/autocomplete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: updatedForm.query })
            });

            if (!response.ok) throw new Error('Failed to fetch suggestions');

            
            const data = await response.json();
            setAiSuggestions(data.result.suggestions); // Use `result` instead of `suggestions`
            console.log("Response from autocomplete API:", data);
            
            // only show the suggestion list if the user actually has something typed in the field
            if(e.target?.value === "") {
                setIsOpen(false);
            } else { 
                setIsOpen(true);
            }                        

        } catch (error) {
            console.error("Autocomplete error:", error);
        }
    };


    // watches "submitSignal" for a submit signal sent from dynamicFormTemplate 
    // handles input field checking on submit and only on submit
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

    // Closes dropdown_list when user clicks outside of the list
    useEffect(() => {    
        const handleClickOutside = (e) => {
        if (textAreaRef.current && !textAreaRef.current.contains(e.target)) {
            setIsOpen(false);
        }
        };

        document.addEventListener('mousedown', handleClickOutside);
        
        return () => {
        document.removeEventListener('mousedown', handleClickOutside);     
        };

    }, []);

    // resizes the field once it detects that the user has selected an suggestion
    useEffect(() => {
        resizeOnInput();
    }, [formPackage[field]]);


    const handleSelect = (option) => {
        setForm({...formPackage, [field]: option});    
        setIsOpen(false);
        setShowEmptyError(false);
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
            
            {isOpen && (
                <div className={styles.suggestionDropDown}>
                    {aiSuggestions.map((suggestion, index) => (                        
                        <div key={index} onMouseDown={() => handleSelect(suggestion)} className={styles.dropdown_item}>
                            {suggestion}
                        </div>
                    ))}
                </div>
            )}

            {showEmptyError && (
                <p className={styles.errorText}>Please fill out this field</p> 
            )}
        </div>
    );
}

export default CustomTextArea;
