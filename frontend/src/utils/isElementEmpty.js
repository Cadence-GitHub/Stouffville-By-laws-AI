export const isElementEmpty = (ElementReference) => {        
  if (!ElementReference) return true;
  return ElementReference.value.trim() === "";
};
