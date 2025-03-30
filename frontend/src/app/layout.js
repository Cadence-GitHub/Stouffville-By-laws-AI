import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="headerContainer">
          <div style={{position: "inherit", backgroundColor: "#0060A1", width: "100%", height: "30px", top: "0%"}}></div> {/* this div is here for design reasons */}
          <div className="centerItems" style={{position: "inherit", backgroundColor: "#FFFFFF",width: "100%", height: "77px", top: "30px"}}>
            <div>
              <h3 style={{color: "#224292", fontWeight: "600", fontStyle: "italic"}}>
                Stouffville By-laws AI Project
              </h3>
            </div>
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
