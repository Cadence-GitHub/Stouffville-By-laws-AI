import styles from "./Footer.module.css";
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

                    <a className={styles.iconLink} href="https://aicircle.ca/" target="_blank" rel="noopener noreferrer">
                        <FontAwesomeIcon icon="globe" style={{ marginRight: '10px' }} />                
                        <span className="clickable-text" style={{color: "white"}}>AI Circle</span>
                    </a>
                </div>
            </div>
        </div>
    );
}

export default Footer;