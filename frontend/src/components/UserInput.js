'use Client'
import { useState } from "react";

const UserInput = ({displayValue}) => {

    // Returns a message based on a randomly generated integer from 0 to whatever the length of the array above:        
    const defaulttMessage = () => {
    
        const starterQueries = ["Can my dog poop on someone else's lawn?", 
                                "What should I put in my blue bins?", 
                                "Do I need to register my dog with the town?"
                               ];        
        let message = starterQueries[Math.floor(Math.random() * starterQueries.length)];

        return message;
    }

    const [userQuery, setUserQuery] = useState(displayValue === '' ? defaulttMessage() : displayValue);
    
    // Triggers when input loses focus from user
    const handleBlur = () => {
        if (userQuery == "") {
            setUserQuery(displayValue === '' ? defaulttMessage() : displayValue);
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

export default UserInput;