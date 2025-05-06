import { useRef } from "react";

const MyTextArea = ({placeholder}) => {

    const textAreaRef = useRef(null);
    const handleInput = () => {
        
        let elementRef = textAreaRef.current;
        if (elementRef) {

            elementRef.style.height = '35px';
            let contentHeight = elementRef.scrollHeight;
            const maxHeight = 70;
    
            if(contentHeight <= maxHeight) {
                elementRef.style.height = contentHeight + 'px'; // Set to scroll height
                elementRef.style.overflow = 'hidden';
            }
            else {
                elementRef.style.height = maxHeight + 'px'; // Set to scroll height
                elementRef.style.overflow = 'auto'; // Reset
            }
        }
    }

    return (
        <div className="input-wrapper">
                <textarea 
                    ref={textAreaRef}
                    className="textarea-input"
                    placeholder={placeholder}
                    onInput={handleInput}
                    row={1}>
                </textarea>
            </div>
    );
}

export default MyTextArea;
