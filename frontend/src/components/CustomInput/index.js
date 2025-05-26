'use Client'
import styles from "./CustomInput.module.css";
import { useState, useRef } from "react";
import MyPlaceHolders from "../PlaceHolderQueries";


const CustomInput = ({displayValue}) => {

    let inputRef = useRef(null);
    let userQuery = null;

    // This also grabs the text user enetered when they press enter    
    const handleEnter = (e) => {                
        
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();    
            
            userQuery = inputRef.current?.value;
            if(userQuery === null || userQuery === "") {
                userQuery = displayValue
                console.log(userQuery);
            }
            else {
                console.log(userQuery);
            }
        }                  
    }


    return (
        <input 
            className={styles.input}
            name="userQuery" 
            ref={inputRef}
            type="text" 
            placeholder={displayValue}
            onKeyDown={handleEnter}
        />
    );
}

export default CustomInput;