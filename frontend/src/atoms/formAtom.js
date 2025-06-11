// src/atoms/formAtoms.js
import { atom } from 'jotai';
import { useAtomValue } from 'jotai';

export const defaultValues = {
    bylaw_status: "active",
    laymans_answer: true,
    query: ""
}

export const form = atom({
    bylaw_status: "active",
    laymans_answer: true,
    query: ""
});

export const submitSignalAtom = atom(false); // Each submit increments this
export const validationResultAtom = atom({}); // Map: componentName: true/false


export const useIsSimpleFormFilled = () => {    
    const formPackage = useAtomValue(form);
    if(formPackage.query.trim() === "") {
        return false;
    } else { 
        return true;
    }
}

export const useIsAdvancedFormFilled = () => {
    const formPackage = useAtomValue(form);
    
    if(formPackage.bylaw_status === defaultValues.bylaw_status && formPackage.laymans_answer === defaultValues.laymans_answer && formPackage.query.trim() === "") {
        return false;
    } else {
        return true;
    }
}