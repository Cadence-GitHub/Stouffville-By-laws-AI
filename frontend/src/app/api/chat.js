import { useAtomValue } from "jotai";
import { advancedForm, simpleForm } from "@/atoms/formAtom";

const Generic = ({type}) => {
    const advancedformPayload = useAtomValue(advancedForm);
    const simpleformPayload = useAtomValue(simpleForm);

    
}

export async function POST(req) {
    
    const payload = GrabValue();
    
    try { 
        const response = await fetch("[API ENDPOINT HERE", {
                method: "POST",
                headers: {"Content-type": "application/json"},
                body: JSON.stringify(payload)
            });
    }
    catch {

    }
}