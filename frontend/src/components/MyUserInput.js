'use Client'
import { useState } from "react";
import MyPlaceHolders from "./MyPlaceHolders";

const MyUserInput = ({displayValue}) => {

    const [userQuery, setUserQuery] = useState(displayValue === '' ? defaulttMessage() : displayValue);
    
    // Triggers when input loses focus from user
    const handleBlur = () => {
        if (userQuery == "") {
            setUserQuery(displayValue === '' ? MyPlaceHolders() : displayValue);
        }
    }
    
    // Update input value when user types
    const handleChange = (e) => {
        setUserQuery(e.target.value);
    };

    return (
        <input 
            className="input"
            name="userQuery" 
            type="text" 
            value={userQuery} 
            onChange={handleChange} // triggers user starts typing
            onBlur={handleBlur} // When the input loses focus, check and reset if empty
            onClick={e => setUserQuery('')}
        />
    );
}

export default MyUserInput;