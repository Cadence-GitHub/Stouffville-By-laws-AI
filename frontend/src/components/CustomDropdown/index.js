'use client';
import { useState, useRef, useEffect } from 'react';
import { useAtom, useAtomValue } from 'jotai'
import { form, submitSignalAtom } from "@/atoms/formAtom.js";
import Image from 'next/image';
import styles from './CustomDropdown.module.css'; // Import CSS file


/**
 * A custom dropdown component that allows users to select from a list of options.
 * Each option is an object with a `value` and `label`. The selected option updates
 * a specified atom field.
 *
 * @param {Array<{ value: string, label: string }>} selection - The list of options to display in the dropdown.
 * @param {string} placeholder - Greyed-out text that guides the user on expected input.
 * @param {string} field - The atom field to update when an option is selected.
 * @returns {JSX.Element} A <div> containing the selected value and a dropdown menu of suggestions.
 */
const CustomDropdown = ({ selection, placeholder, field }) => {

  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(placeholder);
  const [rotation, setRotation] = useState(0);
  const [formPackage, setForm] = useAtom(form);
  const [showEmptyError, setShowEmptyError] = useState(false);
  
  const submitSignal = useAtomValue(submitSignalAtom);
  
  // Holds the list of options the custom dropdown shows
  const options = selection;

  const dropDownRef = useRef(null);

  // Closes dropdown_list when user clicks outside of the list
  useEffect(() => {    
    const handleClickOutside = (e) => {
      if (dropDownRef.current && !dropDownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);     
    };

  }, []);

  // Handles the rotatiom of the dropdown image
  useEffect(() => {
    setRotation(isOpen ? 180 : 0);
  }, [isOpen]);

  // Handles the behaviour of checking whether or not it has a non-empty value  
  useEffect(() => {

    if(!submitSignal) {
      return; // Doesnt do any checking if user has not submmited
    }
    
    if(options.includes(selected)){
      console.log("Dropdown has value");
      setShowEmptyError(false);
    } else { 
      console.log("Dropdown is missing value");
      setShowEmptyError(true);
    }
  }, [submitSignal]);
  
  const handleSelect = (option) => {
    setSelected(option.label);
    setForm({...formPackage, [field]: option.value});    
    setIsOpen(false);
    setShowEmptyError(false);
  };

  const toggleDropdown = () => {
    setIsOpen((prev) => !prev);
  };

  return (    
    <div ref={dropDownRef} className={styles.customDropDownWrapper}>      
      <div className={styles.selectedOption} > {selected} </div>

      <div className={styles.dropdown_overlayImage}>
          <Image 
            onClick={toggleDropdown} 
            className="clickable-image" 
            src="/assets/images/dropdown-arrow.svg"
            height={30} 
            width={30} 
            alt="drop down arrow"
            style={{transform: `rotate(${rotation}deg)`}}
            />            
      </div>
      
      {isOpen && (
        <div className={styles.dropdown_list}>
          {options.map((option) => (
              <div key={option.label} onClick={() => handleSelect(option)} className={styles.dropdown_item}>                  
                  {option.label}
              </div>
          ))}
        </div>
      )}        
    
      {showEmptyError && (
          <p className="errorText">Please fill out this field</p> 
      )}

    </div>
  );
};

export default CustomDropdown;
