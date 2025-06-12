'use client'
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

import CustomTextArea from "../CustomTextArea";
import MyPlaceHolders from "../PlaceHolderQueries";
import CustomDropdown from "../CustomDropdown";

import { useAtom, useSetAtom } from 'jotai';
import { formAtom, submitSignalAtom, defaultValues, useIsSimpleFormFilled, useIsAdvancedFormFilled } from '@/atoms/formAtom';

// Custom hook here will be refactored later - just wanted to get this thing done
export const useIsAllFieldsFilled = (formType) => {
  const simple = useIsSimpleFormFilled();
  const advanced = useIsAdvancedFormFilled();

  if (formType === 1) return simple;
  if (formType === 2) return advanced;
  return false;
};

const DynamicFormTemplate = () => {
    
    // Responsive UI interaction for the input fields (changes text on click)
    // Change the type of form being displayed when 
    // user clicks on <p>Advanced Search<p/> or <p>Simple Search<p/>
    const [useAdvancedForm, setUseAdvancedForm] = useState(false);
    const [useFormLabel, setUseFormLabel] = useState("Switch to Advanced search");
    const [submitSignal, setSubmitSignal] = useAtom(submitSignalAtom);

    const setForm = useSetAtom(formAtom);
    
    // 1: check simple form
    // 2: check advanced form
    const formType = useAdvancedForm ? 2 : 1; 
    const isAllFieldsFilled = useIsAllFieldsFilled(formType);

    useEffect(() => {
        setForm(defaultValues);
        setSubmitSignal(false);        
    }, [setForm]);

    const router = useRouter();       
    const formRef = useRef(null);    
    
    const handleSwitch = () => {
        setUseAdvancedForm(prev => ! prev);
        useFormLabel === "Switch to Advanced search" ? setUseFormLabel("Switch to Simple search") : setUseFormLabel("Switch to Advanced search");
    }    

    
    const handleSubmit = (e) => {
        e.preventDefault();

        setSubmitSignal(true); // triggers children to validate their inputs

        if(useAdvancedForm === false) {
            if(isAllFieldsFilled === true) {
                router.push("/chat-page");
            }

        } else if (useAdvancedForm === true) {            
            if(isAllFieldsFilled === true) {             
                router.push("/chat-page");
            }
        } else {
            setSubmitSignal(false);
        }
    }
    
    return (
        <div>
            <form ref={formRef} onSubmit={(e) => handleSubmit(e)}>                
                {!useAdvancedForm ? (<SimpleForm placeholder={MyPlaceHolders()}/>) : (<AdvancedForm placeholder={MyPlaceHolders()}/>)}                                
            </form>

            <div style={{display: "flex", flexDirection: "column", alignItems: "center"}}>                    
                <p className="clickable-text" onClick={handleSwitch} style={{fontSize: "15px", fontWeight: "550"}}>                        
                    {useFormLabel}
                </p>                                
                <button className="buttonSubmit" type="submit" onClick={(e) => handleSubmit(e)}>Search</button>                
                <button className="buttonRoute" onClick={() => router.push('/faq-page')}>FAQ</button>               
            </div>
        </div>
    );
};

export default DynamicFormTemplate;

const SimpleForm = ({placeholder}) => {    

    return (
        <CustomTextArea field="query" placeholder={placeholder}/>
    );
};


const AdvancedForm = ({placeholder}) => {
    
    return (
        <div className="form">
            <CustomDropdown selection={[{ value: "active", label: "Active By-laws" }, { value: "inactive", label: "Inactive By-laws" }, { value: "all", label: "All By-laws" }]} field="bylaw_status" placeholder={"Active / In-active Bylaws"}/>
            <CustomDropdown selection={[{ value: true, label: "Simple Language" }, { value: false, label: "Legalese Language" }]} field="laymans_answer" placeholder={"Simple / Legalese Language"}/>
            <CustomTextArea field="query" placeholder={placeholder}/>
        </div>
    );
};
