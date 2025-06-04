# Stouffville By-laws AI Frontend

A [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

This react project uses the App Router as URL mapping method. 


## Prototyping Process

You can find the wireframe diagram on this [Figma Project](`https://www.figma.com/design/IMoKBPjtej2NNSNuYrSPsq/By-laws_stouffville_web?node-id=0-1&t=CSR42gcXGMDGnVoF-1`).

## Getting Started

After cloning the repository, `cd` into the frontend folder, then run the following command on your command line:

```
npm install
```

then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Navigation

`src/app/page.js` holds the Homepage of the project - the Main entry point for the user.

`src/app/components/DynamicFormTemplate/index.js` is where the form types are abstracted and encapsulated. 

## Components Specification

Jotai is being used in this project to centralize and coordinate the storing and retrieving of this data.

If a component expects to recieve an input from the user, specifically for the use of sending this data to the backend, you can find two atoms that house two different json structures - one for simple, another for advanced inside of `src/atoms/formAtoms.js`.

Writing to the Atom example :

```javascript
// components/CustomTextArea/index.js

// Import useAtom and the correct atom from the formAtoms.js
import { useAtom } from 'jotai';
import { simpleForm } from '@/atoms/formAtoms.js';

// Provide a prop called "field" which will specify the field this component will populate
// ***IMPORTANT***: The value you provide in field MUST be the same with the field name in the atom; see below this example.
const CustomTextArea = ({placeholder, field, ...props}) => {    
    
    // instantiate the atom so you can write data to it
    const [form, setForm] = useAtom(simpleForm); 

    const resizeOnInput = () => {        
       ...
    }   

    const handleEnter = (e) => {                
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();    
            
            const userQuery = e.target?.value || placeholder;
            
            // write to the atom using setForm()
            // the most important part is [field]: [value]
            // [field] being the field you want to edit the value of inside the atom
            // [value] being the.. value (they say code is supposed to be self-documenting but you cant be too careful ¯\_(ツ)_/¯)
            setForm({ ...form, [field]: userQuery });         
        }                         
    }

    const handleChange = (e) => {

        // Same Concept
        setForm({ ...form, [field]: e.target?.value });
    }

    return (
        <div className={styles.inputWrapper}>
            <textarea 
                className={styles.textareaInput}
                ref={textAreaRef}
                value={form[field] || ''}  {/* form[field] is just accessing the value of [field] that is inside [form] */}
                onInput={resizeOnInput}
                onKeyDown={handleEnter}
                onChange={handleChange}
                placeholder={placeholder}   
                type="text" 
                {...props}
                rows={1}                
                >
            </textarea>
        </div>
    )
} 

```

MUST MATCH WITH JOTAI ATOM FIELD AND SUPPLIED FIELD

```javascript

// src/atoms/formAtoms.js
import { atom } from 'jotai';

export const advancedForm = atom({
    byLawStatus: "",
    languageType: "",
    query: ""
});

export const simpleForm = atom( {
    query: ""
})


// src/components/DyanmicFormTemplate/index.js
const SimpleForm = ({placeholder}) => {    

    return (
        <CustomTextArea field="query" placeholder={placeholder}/>
    );
};


const AdvancedForm = ({placeholder}) => {
    
    return (
        <div className="form">
            <CustomDropdown selection={["..."]} field="byLawStatus" placeholder={"..."}/>
            <CustomDropdown selection={["..."]} field="languageType" placeholder={"..."}/>
            <CustomTextArea field="query" placeholder={placeholder}/>
        </div>
    );
};

```