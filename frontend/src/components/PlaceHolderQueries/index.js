import { useEffect, useState } from "react";

// future feature?: Have this array fed by backend API of frequently asked queries?
const starterQueries = ["Can my dog poop on someone else's lawn?", 
                        "What should I put in my blue bins?", 
                        "Do I need to register my dog with the town?"
                        ];        

const getRandomMessage = () => {
    return starterQueries[Math.floor(Math.random() * starterQueries.length)];
}

/**
 * Returns a randomly selected placeholder message from a predefined list within `PlaceHolderQueries/index.js`
 * Useful for displaying dynamic hints or suggestions in input fields.
 *
 * @returns {string} A randomly selected placeholder string.
 */
const PlaceHolderQueries = () => {

    const [placeHolder, setPlaceHolder] = useState('');

    useEffect(() => {
        setPlaceHolder(getRandomMessage());
    }, []);
    
    return placeHolder;
}

export default PlaceHolderQueries;