'use Client'
import { useState } from "react";
import Image from "next/image";
import searchIcon from "@/assets/images/search.png"

const DynamicInput = () => {

    // Responsive UI interaction for the input fields (changes text on click)
    // TODO-feature: Have a list of defaultValues to randomly assign to initialValue.
    let initialValue = "Can my dog poop on someone else's lawn?"
    const [userQuery, setUserQuery] = useState(initialValue);
    
    // Triggers when input loses focus from user
    const handleBlur = () => {
        if (userQuery == "") {
            setUserQuery(initialValue);
        }
    }
    
    // Update input value when user types
    const handleChange = (e) => {
        setUserQuery(e.target.value);
    };

    let isOfficer;
    const [officerFlag, useOfficerFlag] = useState(false);
    const HandleClick = (e) => {
        // unchecked -> check
        // checked -> unchecked
        
        isOfficer = officerFlag == false ? true : false;

        useOfficerFlag(isOfficer);  
    };

    
    return (
        <div style={{margin: 22.5}}>
            <form>
                <input 
                    className="input"
                    name="userQuery" 
                    type="text" 
                    value={userQuery} 
                    onChange={handleChange} 
                    defaultValue={userQuery} 
                    onBlur={handleBlur} // When the input loses focus, check and reset if empty
                    onClick={e => setUserQuery('')}/>
                
                {/* <Image src={searchIcon} alt="search" width={20} height={20}/> */}
                {/* TODO-feature: change user input to a form template onClick*/}
                <p style={{fontSize: "15px", color: "#0060A1", fontWeight: "550", margin: 22.5}}>Advanced Search</p>
            
                {/* This element is a flag that changes the output that tailored to law enforcement officer language*/}
                <button type="button" style={{margin: 22.5}} className="buttonState" onClick={HandleClick}>
                    Im an Officer
                    
                    <input name="officerFlag" type="checkbox" className="custom-checkbox" checked={officerFlag} />
                </button>
            
                <button style={{margin: 22.5}} className="buttonSubmit">Search</button>
            </form>
        </div>
    );
};

export default DynamicInput;