// **************************************************
// **************************************************
// UNUSED AT THE MOMENT - REPLACED BY CUSTOM DROPDOWN
// **************************************************
// **************************************************

'use Client'
import styles from "./CustomInput.module.css";
import { useAtom } from 'jotai';
import { formAtom } from '@/atoms/formAtoms';


const CustomInput = ({displayValue, field, ...props}) => {
    
    const [form, setForm] = useAtom(formAtom);

    const handleEnter = (e) => {                
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();    
            
            const userQuery = e.target?.value || displayValue;
            setForm({ ...form, [field]: userQuery });
            console.log(userQuery);        
        }                         
    }

    const handleChange = (e) => {
        setForm({ ...form, [field]: e.target?.value });
    };

    return (
        <input 
            className={styles.input}
            value={form[field] || ''}
            onChange={handleChange}
            onKeyDown={handleEnter}
            placeholder={displayValue}
            type="text"             
            {...props}
        />
    );
}

export default CustomInput;