'use client'
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAtomValue } from 'jotai';
import { form } from "@/atoms/formAtom.js";

import CustomTextArea from "../CustomTextArea";
import MyPlaceHolders from "../PlaceHolderQueries";
import CustomDropdown from "../CustomDropdown";

const DynamicFormTemplate = () => {
    
    // Responsive UI interaction for the input fields (changes text on click)
    // Change the type of form being displayed when 
    // user clicks on <p>Advanced Search<p/> or <p>Simple Search<p/>
    const [useAdvancedForm, setUseAdvancedForm] = useState(false);
    const [useFormLabel, setUseFormLabel] = useState("Switch to Advanced search");

    const router = useRouter();       
    const formPackage = useAtomValue(form);
    
    const handleSwitch = () => {
        setUseAdvancedForm(prev => ! prev);
        useFormLabel === "Switch to Advanced search" ? setUseFormLabel("Switch to Simple search") : setUseFormLabel("Switch to Advanced search");
    }

    // TODO: Get the information the user has passed and pipe it to the backend for processing.
    // TODO: Sanitize input as well.
    // TODO: Disable submitting after user has submitted query, then re-enable after backend has reponded.      
    const handleSubmit = (e) => {
        e.preventDefault();

        // Capture user query
        console.log(formPackage.bylaw_status);
        console.log(formPackage.laymans_answer);
        console.log(formPackage.query);
        
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
            <form onSubmit={(e) => handleSubmit(e)}>                
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
            <CustomDropdown selection={[{ value: "active", label: "Active By-laws" }, { value: "inactive", label: "Inactive By-laws" }, { value: 2, label: "All By-laws" }]} field="bylaw_status" placeholder={"Active / In-active Bylaws"}/>
            <CustomDropdown selection={[{ value: true, label: "Simple Language" }, { value: false, label: "Legalese Language" }]} field="laymans_answer" placeholder={"Simple / Legalese Language"}/>
            <CustomTextArea field="query" placeholder={placeholder}/>
        </div>
    );
};
