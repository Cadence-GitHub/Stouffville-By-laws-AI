'use client'
import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import CustomInput from "../CustomInput";
import CustomTextArea from "../CustomTextArea";
import MyPlaceHolders from "../PlaceHolderQueries";
import santizeInput from "../santizeInput";
import { FallbackMode } from "next/dist/lib/fallback";

const DynamicFormTemplate = () => {
    
    // Responsive UI interaction for the input fields (changes text on click)
    // Change the type of form being displayed when 
    // user clicks on <p>Advanced Search<p/> or <p>Simple Search<p/>
    const [useAdvancedForm, setUseAdvancedForm] = useState(false);
    const [useFormLabel, setUseFormLabel] = useState("Switch to Advanced search");

    const handleSwitch = () => {
        setUseAdvancedForm(prev => ! prev);
        
        useFormLabel === "Switch to Advanced search" ? 
        setUseFormLabel("Switch to Simple search") : 
        setUseFormLabel("Switch to Advanced search");
    }

    // Officer type output flag *TODO feature*
    const [isOfficerFlag, useOfficerFlag] = useState(false);
    const HandleClick = (e) => {
        // unchecked -> check
        // checked -> unchecked

        useOfficerFlag(isOfficerFlag == false ? true : false);  
    };

    // TODO: Get the information the user has passed and pipe it to the backend for processing.
    // TODO: Sanitize input as well.
    // TODO: Disable submitting after user has submitted query, then re-enable after backend has reponded.
    
    const router = useRouter();        
    const [userQueryText, setUserQueryText] = useState('');
    const handleSubmit = (e, userTextEntered) => {
        e.preventDefault();
        
        // Capture user query
        console.log(userTextEntered);
        console.log("DynamicFormTemp: \"Handle Submit\"");
        
        // sanitize input 
        // santizeInput(userQueryText);
        
        // set flag for advanced (legalese) or simple response - i am an officer
        // construct JSON payload                
        
        // recieve backend response and send it to the chatpage to be rendered
        
        // route user to chat-page
        router.push("/chat-page")

    }

    
    return (
        <div>
            <form onSubmit={(e, userText) => handleSubmit(e, userText)}>
                
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
        <CustomTextArea placeholder={placeholder}/>
    );
};


const AdvancedForm = ({placeholder}) => {
    
    return (
        <div className="form">
            <CustomInput displayValue={"Category"}/>
            <CustomInput displayValue={"Keywords (separated by \',\')"}/>
            <CustomTextArea placeholder={placeholder}/>
        </div>
    );
};
