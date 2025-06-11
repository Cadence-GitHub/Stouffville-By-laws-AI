export async function POST(request) {
  try {
    const body = await request.json();
    const { query } = body;

    console.log("Received formPackage:", body);

    const externalResponse = await fetch('https://bylaws.aicircle.ca/api/autocomplete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!externalResponse.ok) {
      console.error('External API error:', externalResponse.statusText);
      return new Response(JSON.stringify({ error: 'Failed to fetch from external API' }), {
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

    return new Response(JSON.stringify({ error: "Invalid request", details: err.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
