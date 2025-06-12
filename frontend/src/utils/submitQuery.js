const submitQuery = async ({ query, bylaw_status, laymans_answer }) => {
  try {
    console.log("in submitQuery!")
    const response = await fetch('api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        bylaw_status,
        laymans_answer,
      }),
    });

    if (!response.ok) throw new Error('Failed to submit');

    const data = await response.json();
    console.log("Response from API:", data);
        
    return data;    

  } catch (error) {
    console.error("Submission error:", error);
    return null;
  }
};

export default submitQuery;
