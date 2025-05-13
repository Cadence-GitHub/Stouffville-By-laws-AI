import styles from "./Footer.module.css";

const Footer = () => {
    return (
        <div className="centerHorizontal">
            <div className={styles.footer}>
                <div>
                    This AI tool provides general information about Stouffville by-laws and should not be considered legal advice.                    
                </div>
            </div>        
        </div>

    );
}

export default Footer;