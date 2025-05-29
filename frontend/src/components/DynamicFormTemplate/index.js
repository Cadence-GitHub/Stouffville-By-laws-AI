'use client'
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAtomValue } from 'jotai';
import { formAtom } from "@/atoms/formAtoms";

import Image from "next/image";
import CustomTextArea from "../CustomTextArea";
import CustomInput from "../CustomInput";
import MyPlaceHolders from "../PlaceHolderQueries";
import CustomDropdown from "../CustomDropdown";

const DynamicFormTemplate = () => {
    
    // Responsive UI interaction for the input fields (changes text on click)
    // Change the type of form being displayed when 
    // user clicks on <p>Advanced Search<p/> or <p>Simple Search<p/>
    const [useAdvancedForm, setUseAdvancedForm] = useState(false);
    const [useFormLabel, setUseFormLabel] = useState("Switch to Advanced search");

    const router = useRouter();       
    const formInfo = useAtomValue(formAtom);
    
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
        console.log(formInfo.category);
        console.log(formInfo.keywords);
        console.log(formInfo.query);
        
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
                
                <div>
                    <p className="clickable-text" onClick={handleSwitch} style={{fontSize: "15px", fontWeight: "550"}}>                        
                        {useFormLabel}
                    </p>    
                
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


const AdvancedForm = ({placeholder, handleSelect}) => {
    
    return (
        <div className="form">
            <CustomDropdown selection={["Active By-laws", "Inactive By-laws", "All By-laws"]} placeholder={"Active / In-active Bylaws"}/>
            <CustomDropdown selection={["Simple Language", "Legalese Language"]} placeholder={"Simple / Legalese Language"}/>
            <CustomTextArea field="query" placeholder={placeholder}/>
        </div>
    );
};
