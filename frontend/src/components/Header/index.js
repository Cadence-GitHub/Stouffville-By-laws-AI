'use client'
import { useRouter } from "next/navigation";
import styles from "./Header.module.css";
import "@/styles/globals.css";

const Header = () => {
    
    const router = useRouter(); 

    return (
        <div className={styles.header}>
            <div className={styles.headerTrim}/>
            <h2 className="clickable-text" onClick={() => router.push('/')}>Stouffville By-Laws AI Project</h2>                            
            <p className={styles.subtitle}>Your bylaw questions answered in plain simple language</p>
        </div>
    );
}

export default Header;