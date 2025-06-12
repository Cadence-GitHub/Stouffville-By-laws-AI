export async function POST(request) {
  try {
    const body = await request.json();
    const { query, byLaw_Status, laymans_answer } = body;

    console.log("Received formPackage:", body);

    const externalResponse = await fetch('https://bylaws.aicircle.ca/api/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, status: byLaw_Status }),
    });

    // Handle 429 Rate Limit
    if (externalResponse.status === 429) {
      const errorText = await externalResponse.text();
      console.warn("Rate limit hit:", errorText);

      return new Response(JSON.stringify({
        error: "Rate limit exceeded. Please try again later.",
        details: errorText
      }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle other errors from external API
    if (!externalResponse.ok) {
      const errorText = await externalResponse.text();
      console.error('External API error:', externalResponse.status, errorText);

      return new Response(JSON.stringify({ error: 'Failed to fetch from external API', details: errorText }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const data = await externalResponse.json();
    return new Response(JSON.stringify({ status: "ok", result: data }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (err) {
    console.error("API error:", err);

    return new Response(JSON.stringify({
      error: "Invalid request",
      details: err.message
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

