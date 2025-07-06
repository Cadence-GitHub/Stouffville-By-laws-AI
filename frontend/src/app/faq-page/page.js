'use client'
import { useRouter } from "next/navigation";

const FAQ = () => {
    
    const router = useRouter();
    
    return (        
        <div className="contentContainer">
            <div style={{marginBottom: "50px"}}>
                <h1>Frequently Asked Questions</h1>
            </div>
            
            <div style={{alignSelf: "center", width: "60%"}}>                
                <div className="qaPair">
                    <h3>Q: Is this project a Stouffville Town Initiative?</h3>

                    <div style={{display: "flex", flexDirection: "row", gap: "8px"}}>
                        <h3>A:</h3>
                        <p>No, we are just a small group of Stouffville residents with a strong passion in using our programming skills and knowledge of AI (LLM) models to provide accessibility to the rich yet complicated collection of by-laws in Stouffville.</p>
                    </div>
                </div>
                

                <div className="qaPair">
                    <h3>Q: Are there plans for multi-lingual support?</h3>
                                                    
                    <div style={{display: "flex", flexDirection: "row", gap: "8px"}}>
                        <h3>A:</h3>
                        <p>Yes, we are actively incorporating ways to provide accessibility to a diverse range of users.</p>
                    </div>
                </div>                


                <div className="qaPair">
                    <h3>Q: I would like provide feedback to this project, where do I go?</h3>
                                                    
                    <div style={{display: "flex", flexDirection: "row", gap: "8px"}}>
                        <h3>A:</h3>
                        <p>The community website is linked below where we are more than happy to hear how we can improve the experiece!</p>
                    </div>
                </div>
                
                
                <div className="qaPair">
                    <h3>Q: I would like to join this community and contribute to this project, where do I go?</h3>
                                                    
                    <div style={{display: "flex", flexDirection: "row", gap: "8px"}}>
                        <h3>A:</h3>
                        <p>The community website and GitHub project is linked below, come and say hi!</p>
                    </div>
                </div>


                <button className="buttonSubmit" onClick={() => router.push('/')}>Start asking questions</button>            
            </div>

        </div>
    );
}

export default FAQ;