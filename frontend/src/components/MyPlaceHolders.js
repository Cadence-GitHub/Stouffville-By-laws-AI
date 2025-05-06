import { useEffect, useState } from "react";

// future feature?: Have this array fed by backend API of frequently asked queries?
const starterQueries = ["Can my dog poop on someone else's lawn?", 
                        "What should I put in my blue bins?", 
                        "Do I need to register my dog with the town?"
                        ];        

const getRandomMessage = () => {
    return starterQueries[Math.floor(Math.random() * starterQueries.length)];
}

// Returns a message based on a randomly generated integer from 0 to whatever the length of the array above:        
const MyPlaceHolders = () => {   
    const [placeHolder, setPlaceHolder] = useState('');

    useEffect(() => {
        setPlaceHolder(getRandomMessage());
    }, []);
    
    return placeHolder;
}

export default MyPlaceHolders;