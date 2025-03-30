'use client'

import styles from "./page.module.css";
import { useState } from "react";

export default function Home() {
  
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
  
  return (
    <div className="contentContainer">
      <div className="centerItems">
        
        {/* I wanted a 45px gap between the p and button, hence the hardcoded margins */}
        <p style={{fontWeight: "500", color: "#0060A1", marginBottom: 22.5}}> 
          What would you like to know?
        </p>
        
        {/* TODO: Button routes to a FAQ page */}
        <div style={{margin: 22.5}}>
          <button className="buttonRoute">
            FAQ
          </button>
        </div>

        <div>
          <form>
            <input 
              name="userQuery" 
              type="text" 
              value={userQuery} 
              onChange={handleChange} 
              defaultValue={userQuery} 
              onBlur={handleBlur} // When the input loses focus, check and reset if empty
              onClick={e => setUserQuery('')} >
            </input>
            <button type="submit">Search</button>
          </form>
        </div>


      </div>
    </div>
  );
}
