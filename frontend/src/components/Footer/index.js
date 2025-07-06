import styles from "./Footer.module.css";
import Image from "next/image";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Footer = () => {
    return (        
        <div className={styles.footerWrapper}>
            <div className={styles.footer}>
                <div>                        
                    This AI tool provides general information about Stouffville by-laws and should not be considered legal advice.                                
                </div>
                <div className={styles.footerLinks}>
                    <a className={styles.iconLink} href="https://github.com/Cadence-GitHub/Stouffville-By-laws-AI" target="_blank" rel="noopener noreferrer">
                        <FontAwesomeIcon icon={['fab', 'github']} style={{ marginRight: '10px' }} />
                        <span className="clickable-text" style={{color: "white"}}>GitHub</span>
                            
                    </a>

                    <span style={{fontSize: "25px"}}>|</span>

                    <a className={styles.iconLink} style={{position: "relative",  bottom: "4px"}} href="https://aicircle.ca/" target="_blank" rel="noopener noreferrer">                        
                        <Image style={{marginRight: '10px'}}  src="/assets/images/AICIRCLE_LOGO.png" height={40} width={40} alt="AI Circle Logo"/>
                        <span className="clickable-text" style={{position: "relative", color: "white", bottom: "15px"}}>AI Circle Website</span>                        
                    </a>
                </div>
            </div>
        </div>
    );
}

export default Footer;