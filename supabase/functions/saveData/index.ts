// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import * as postgres from 'https://deno.land/x/postgres@v0.14.2/mod.ts'

const databaseUrl = 'postgresql://postgres:xAWB2QRSpEHvMegV@db.dnhcuemnhgdglyjvslxf.supabase.co:5432/postgres'
// Create a database pool with three connections that are lazily established
const pool = new postgres.Pool(databaseUrl, 3, true)

serve(async (req) => {
  const { message } = await req.json()
  const response = {
    messageId: message.messageId,
    data: message.data,
    publishTime: message.publishTime,
    databaseUrl: databaseUrl,
  }
  try {
    // Grab a connection from the pool
    const connection = await pool.connect()
    try {
      // Execute a query on the connection
      const result = await connection.queryObject("INSERT INTO transactions (message_id, data, publish_time) VALUES ($1, $2, $3)", response.messageId, response.data, response.publishTime)
      // Return the response with the correct content type header
      return new Response(
        JSON.stringify(result),
        { headers: { "Content-Type": "application/json" } },
      )
      
  } finally {
    // Release the connection back to the pool
    connection.release()
  }
  } catch (error) {
    // Return the error with the correct content type header
    return new Response(error.toString(), {
      status: 500,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
      },
    })
  }
})

// To invoke:
// curl -i --location --request POST 'http://localhost:54321/functions/v1/' \
//   --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
//   --header 'Content-Type: application/json' \
//   --data '{"name":"Functions"}'
