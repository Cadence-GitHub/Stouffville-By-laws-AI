'use Client'
import { useState } from "react";
import Image from "next/image";
import UserInput from "./UserInput";


const DynamicForms = ({startChat}) => {
    
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
    const handleSubmit = (e) => {
        e.preventDefault();
        startChat();
    }

    
    return (
        <div style={{margin: 22.5}}>
            <form onSubmit={handleSubmit}>
                
                {!useAdvancedForm ? (<SimpleForm/>) : (<AdvancedForm/>)}
                
                <div className="input-wrapper">
                    <button className="submitButtonQuery" style={{left: "120px", bottom: "75px"}}>
                        <Image 
                            src="/assets/images/search.png" 
                            alt="search" 
                            width={15} 
                            height={15}
                        />
                    </button>
                </div>
                
                {/* TODO-feature: change user input to a form template onClick*/}
                <p className="clickable-text" style={{fontSize: "15px", color: "#0060A1", fontWeight: "550", margin: 22.5}} onClick={handleSwitch}>{useFormLabel}</p>
            
                {/* This element is a flag that changes the output that tailored to law enforcement officer language*/}
                <button type="button" style={{margin: 22.5}} className="buttonState" onClick={HandleClick}>
                    Im an Officer
                    
                    <input name="officerFlag" type="checkbox" className="custom-checkbox" checked={isOfficerFlag} readOnly />
                </button>
            
                <button type="submit" style={{margin: 22.5}} className="buttonSubmit">Search</button>
            </form>
        </div>
    );
};

export default DynamicForms;

const SimpleForm = () => {
    return (
        <UserInput displayValue={''}/>
    );
};


const AdvancedForm = () => {
    return (
        <div className="form">
            <UserInput displayValue={"Category"}/>
            <UserInput displayValue={"Keywords"}/>
            <UserInput displayValue={''}/>
        </div>
    );
};
