'use client';
import { useState, useRef, useEffect } from 'react';
import { useAtom } from 'jotai'
import { form } from "@/atoms/formAtom.js";

import Image from 'next/image';
import styles from './CustomDropdown.module.css'; // Import CSS file

const CustomDropdown = ({ selection, placeholder, field}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(placeholder);
  const [rotation, setRotation] = useState(0);
  const [formPackage, setForm] = useAtom(form);
  
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
  
  const handleSelect = (option) => {
    setSelected(option.label);
    setForm({...formPackage, [field]: option.value});    
    setIsOpen(false);
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
            alt="send button image"
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
    </div>
  );
};

export default CustomDropdown;
