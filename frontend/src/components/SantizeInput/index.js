const santizeInput = ({query}) => {

    let santized;
    
    if(query !== "") {
       santized = query; 
    }

    return santized;

}

export default santizeInput;