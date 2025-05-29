import { useAtomValue } from "jotai";
import { atomForms } from "@/atoms/formAtoms";

const GrabValue = () => {
    const formPayload = useAtomValue(atomForms);

    return formPayload;
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