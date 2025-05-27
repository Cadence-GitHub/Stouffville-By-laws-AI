// src/atoms/formAtoms.js
import { atom } from 'jotai';

export const formAtom = atom({
    category: "",
    keywords: [""],
    officerFlag: false,
    bylawStatus: "active",
    query: ""
});
