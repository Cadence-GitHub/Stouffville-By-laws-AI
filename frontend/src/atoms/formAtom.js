// src/atoms/formAtoms.js
import { atom } from 'jotai';
import { useAtomValue } from 'jotai';

export const submitSignalAtom = atom(false); 
export const successSignalAtom = atom(0); // Subscribed components increments this + 1; 

export const defaultValues = {
    bylaw_status: "active",
    laymans_answer: true,
    query: ""
}

export const formAtom = atom({
    bylaw_status: "active",
    laymans_answer: true,
    query: ""
});


export const useIsSimpleFormFilled = () => {    
    const formPackage = useAtomValue(formAtom);
    const cleanQuery = String(formPackage.query || "").trim();

    if(cleanQuery === "") {
        return false;
    } else { 
        return true;
    }
}

export const useIsAdvancedFormFilled = () => {
  const formPackage = useAtomValue(formAtom);
  const cleanQuery = String(formPackage.query || "").trim();

  const sameBylaw = formPackage.bylaw_status === defaultValues.bylaw_status;
  const sameLanguage = formPackage.laymans_answer === defaultValues.laymans_answer;
  const isQueryEmpty = cleanQuery === defaultValues.query;

  return !(sameBylaw && sameLanguage && isQueryEmpty);
};
