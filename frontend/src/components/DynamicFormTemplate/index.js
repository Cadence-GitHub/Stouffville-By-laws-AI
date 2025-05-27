'use client'
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAtomValue } from 'jotai';
import { formAtom } from "@/atoms/formAtoms";

import Image from "next/image";
import CustomInput from "../CustomInput";
import CustomTextArea from "../CustomTextArea";
import MyPlaceHolders from "../PlaceHolderQueries";

const DynamicFormTemplate = () => {
    
    // Responsive UI interaction for the input fields (changes text on click)
    // Change the type of form being displayed when 
    // user clicks on <p>Advanced Search<p/> or <p>Simple Search<p/>
    const [useAdvancedForm, setUseAdvancedForm] = useState(false);
    const [useFormLabel, setUseFormLabel] = useState("Switch to Advanced search");
    const [isOfficerFlag, useOfficerFlag] = useState(false);

    const router = useRouter();       
    const formInfo = useAtomValue(formAtom);

    const handleSwitch = () => {
        setUseAdvancedForm(prev => ! prev);
        useFormLabel === "Switch to Advanced search" ? setUseFormLabel("Switch to Simple search") : setUseFormLabel("Switch to Advanced search");
    }

    // Officer type output flag *TODO feature*
    const HandleClick = (e) => {
        // unchecked -> check
        // checked -> unchecked
        useOfficerFlag(isOfficerFlag == false ? true : false);  
    };

    // TODO: Get the information the user has passed and pipe it to the backend for processing.
    // TODO: Sanitize input as well.
    // TODO: Disable submitting after user has submitted query, then re-enable after backend has reponded.      
    const handleSubmit = (e) => {
        e.preventDefault();
        
        // Capture user query
        console.log(formInfo.category);
        console.log(formInfo.keywords);
        console.log(formInfo.query);
        
        // sanitize input 
        // santizeInput(userQueryText);
        
        // set flag for advanced (legalese) or simple response - i am an officer
        // construct JSON payload                
        
        // recieve backend response and send it to the chatpage to be rendered
        
        // route user to chat-page
        // router.push("/chat-page")
    }

    
    return (
        <div>
            <form onSubmit={(e) => handleSubmit(e)}>
                
                {!useAdvancedForm ? (<SimpleForm placeholder={MyPlaceHolders()}/>) : (<AdvancedForm placeholder={MyPlaceHolders()}/>)}
                
                <div>
                    <p className="clickable-text" onClick={handleSwitch} style={{fontSize: "15px", fontWeight: "550"}}>                        
                        {useFormLabel}
                    </p>
                
                    {/* This element is a flag that changes the output that tailored to law enforcement officer language*/}
                    <button type="button" className="buttonState" onClick={HandleClick}>
                        Im an Officer                        
                        <input name="officerFlag" type="checkbox" className="custom-checkbox" checked={isOfficerFlag} readOnly />
                    </button>
                
                    <button type="submit" className="buttonSubmit">Search</button>
                </div>
            </form>
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
            <CustomInput field="category" displayValue={"Category"}/>
            <CustomInput field="keywords" displayValue={"Keywords (separated by \',\')"}/>
            <CustomTextArea field="query" placeholder={placeholder}/>
        </div>
    );
};
