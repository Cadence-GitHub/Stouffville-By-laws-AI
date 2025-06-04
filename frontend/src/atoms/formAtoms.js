// src/atoms/formAtoms.js
import { atom } from 'jotai';

export const advancedForm = atom({
    bylaw_status: "",
    laymans_answer: "",
    query: ""
});

export const simpleForm = atom( {
    query: ""
})
