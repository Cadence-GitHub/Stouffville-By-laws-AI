'use client'
import { Geist, Geist_Mono } from "next/font/google";
import { useRouter } from "next/navigation";
import "../styles/globals.css";

export default function RootLayout({ children }) {
  
  const router = useRouter();
  
  return (
    <html lang="en">
      <body>
        <div className="headerContainer">
          <div style={{position: "inherit", backgroundColor: "#0060A1", width: "100%", height: "30px", top: "0%"}}></div> {/* this div is here for design reasons */}
          <div className="centerItems" style={{position: "inherit", backgroundColor: "#FFFFFF",width: "100%", height: "77px", top: "30px"}}>
            <div>
              <h3 className="clickable-text" onClick={() => router.push('/')} style={{color: "#224292", fontWeight: "600", fontStyle: "italic"}}>
                Stouffville By-laws AI Project
              </h3>
            </div>
          </div>
        </div>
        <div>
          {children}        
        </div>
      </body>
    </html>
  );
}
