import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { Provider } from 'jotai'
import "@/styles/globals.css";
import "@/lib/fontawesome";


export const metadata = {
  title:  "Stouffville By-Laws AI Project",
  description: "This project is made to help users in navigating Stouffville's by-laws, breaking down the complicated legal language into simpler language to be easily understood.",
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Provider>
          <Header/> 
          {children}
          <Footer/>
        </Provider>
      </body>
    </html>
  );
}
