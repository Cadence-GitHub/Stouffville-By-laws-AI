'use client'
import { useRef, useEffect, useState } from "react";
import { useAtom, useAtomValue } from 'jotai';
import { formAtom, submitSignalAtom } from "@/atoms/formAtom.js";
import styles from "./CustomTextArea.module.css"

/**
 * A custom textarea component that dynamically resizes based on user input.
 * It also displays a dropdown list of suggested results retrieved from an API.
 *
 * @param {string} placeholder - Greyed-out text that guides the user on expected input.
 * @param {string} field - The atom field to update when a suggestion is selected.
 * @returns {JSX.Element} A container `<div>` with a `<textarea>` and a dropdown of suggestions.
 */
const CustomTextArea = ({ placeholder, field, ...props }) => {
    const textAreaRef = useRef(null);
    const [isOpen, setIsOpen] = useState(false);
    const [formPackage, setForm] = useAtom(formAtom);
    const [showEmptyError, setShowEmptyError] = useState(false);
    const [aiSuggestions, setAiSuggestions] = useState([]);
    const submitSignal = useAtomValue(submitSignalAtom);
    
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
            
            if(e.target.value.trim() === "") {

                e.preventDefault(); 
                setShowEmptyError(true);
                textAreaRef.current?.focus();    

            } else { 

                e.preventDefault();                            
                setForm({ ...formPackage, [field]: String(e.target?.value).trim()});                                    
                e.target.form?.requestSubmit();      
            }                        
        }                         
    }

    // fetches auto complete suggestions and controls when the list of suggestions show
    const handleChange = async (e) => {

        const updatedForm = { ...formPackage, [field]: String(e.target?.value)};
        setForm(updatedForm);
        setShowEmptyError(false);        
        
        try {                  
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

        if(textAreaRef.current.value.trim() === "") {
            setShowEmptyError(true);
        } else { 
            setShowEmptyError(false);
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

    // Executes after user clicks a suggestion on the dropdown list
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
