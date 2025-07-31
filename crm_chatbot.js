
import axios from 'axios';
import OpenAI from 'openai';
import dotenv from 'dotenv';
import fs from 'fs';
import readline from 'readline';

dotenv.config();

const {
  CLIENT_ID,
  CLIENT_SECRET,
  REFRESH_TOKEN,
  API_DOMAIN,
  ACCOUNTS_URL,
  OPENAI_API_KEY
} = process.env;

let accessToken = process.env.ACCESS_TOKEN || null;

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

async function refreshAccessToken() {
  try {
    const params = new URLSearchParams({
      refresh_token: REFRESH_TOKEN,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      grant_type: 'refresh_token'
    });

    const res = await axios.post(`${ACCOUNTS_URL}`, params);
    accessToken = res.data.access_token;

    console.log("New Access Token Fetched:", accessToken);
    saveTokenToEnv(accessToken);
    return accessToken;
  } catch (err) {
    console.error("Error refreshing token:", err.response?.data || err.message);
    throw err;
  }
}

function saveTokenToEnv(newToken) {
  const envPath = '.env';
  let envContent = fs.readFileSync(envPath, 'utf8');

  if (envContent.includes('ACCESS_TOKEN=')) {
    envContent = envContent.replace(/ACCESS_TOKEN=".*"/, `ACCESS_TOKEN="${newToken}"`);
  } else {
    envContent += `\nACCESS_TOKEN="${newToken}"\n`;
  }

  fs.writeFileSync(envPath, envContent);
}

async function getHeaders() {
  if (!accessToken) {
    accessToken = await refreshAccessToken();
  }
  return {
    Authorization: `Zoho-oauthtoken ${accessToken}`,
    "Content-Type": "application/json",
  };
}


async function searchZoho(module, criteria) {
  const headers = await getHeaders();
  try {
    const res = await axios.get(`${API_DOMAIN}/crm/v2/${module}/search`, {
      headers,
      params: { criteria },
    });
    return res.data.data || [];
  } catch (err) {
    if (err.response?.status === 204) return [];
    throw err;
  }
}

async function createZohoObject(module, data) {
  const headers = await getHeaders();
  const res = await axios.post(`${API_DOMAIN}/crm/v2/${module}`, { data: [data] }, { headers });
  return res.data;
}

async function updateZohoObject(module, id, data) {
  const headers = await getHeaders();
  const res = await axios.put(`${API_DOMAIN}/crm/v2/${module}/${id}`, { data: [data] }, { headers });
  return res.data;
}

async function findUserByName(name) {
  const headers = await getHeaders();
  const res = await axios.get(`${API_DOMAIN}/crm/v2/users`, {
    headers,
    params: { type: "ActiveUsers" },
  });
  const user = res.data.users.find(u =>
    u.full_name.toLowerCase().includes(name.toLowerCase())
  );
  return user ? user.id : null;
}

async function findContactByName(name) {
  const contacts = await searchZoho("Contacts", `(Full_Name:equals:${name})`);
  return contacts.length ? contacts[0].id : null;
}

async function analyzeCommand(command) {
  const prompt = `
You are a CRM command analyzer for Zoho CRM operations. Analyze the user's natural language command and determine what CRM operation should be performed.

Respond with a JSON object containing:
- "operation": one of "create_account", "update_deal_stage", "create_deal", or "unknown"
- "data": relevant fields extracted, including optional "contact_name" and "closing_date" for deals.

Example:
{"operation": "create_deal", "data": {"account_name": "Acme Corp", "deal_name": "Big Deal", "amount": 1000, "stage": "Qualification", "contact_name": "John Doe", "closing_date": "2025-08-15"}}
`;

  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: prompt },
      { role: "user", content: command },
    ],
    temperature: 0,
  });

  let rawContent = response.choices[0].message.content.trim();
  rawContent = rawContent.replace(/```json|```/g, '').trim();

  return JSON.parse(rawContent);
}

async function executeCommand(analysis) {
  const { operation, data } = analysis;

  switch (operation) {
    case "create_account":
      return await createZohoObject("Accounts", {
        Account_Name: data.account_name,
        Phone: data.phone,
        Website: data.website,
        Industry: data.industry,
        Annual_Revenue: data.annual_revenue,
      });

    case "create_deal": {
      const dealName = data.deal_name || `${data.account_name || "Unnamed"} Deal`;
      const amount = data.amount || data.deal_amount || 0;
      const stage = data.stage || "Qualification";
      const closingDate = data.closing_date || null;

      // Find Account ID if provided
      let accountId = null;
      if (data.account_name) {
        const accounts = await searchZoho("Accounts", `(Account_Name:equals:${data.account_name})`);
        if (accounts.length) accountId = accounts[0].id;
      }
      let contactId = null;
      if (data.contact_name) {
        contactId = await findContactByName(data.contact_name);
      }

      return await createZohoObject("Deals", {
        Deal_Name: dealName,
        Amount: amount,
        Stage: stage,
        ...(closingDate && { Closing_Date: closingDate }),
        ...(accountId && { Account_Name: { id: accountId } }),
        ...(contactId && { Contact_Name: { id: contactId } }),
      });
    }
case "update_deal_stage": {
  const deals = await searchZoho("Deals", `(Deal_Name:contains:${data.deal_name})`);
  if (!deals.length) throw new Error(`Deal not found: ${data.deal_name}`);

  const stageMap = {
    "qualification": "Qualification",
    "needs analysis": "Needs Analysis",
    "value proposition": "Value Proposition",
    "proposal": "Proposal/Price Quote",
    "proposal/price quote": "Proposal/Price Quote",
    "negotiation": "Negotiation/Review",
    "negotiation/review": "Negotiation/Review",
    "closed won": "Closed Won",
    "closed lost": "Closed Lost"
  };

  let stageValue = data.new_stage || data.stage;
  if (!stageValue) throw new Error("No stage provided for update.");

  stageValue = stageMap[stageValue.toLowerCase()] || stageValue;

  console.log(`Updating deal ${deals[0].id} to stage: ${stageValue}`);

  return await updateZohoObject("Deals", deals[0].id, { Stage: stageValue });
}


    default:
      return { message: "Unknown or unsupported operation" };
  }
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

rl.question("Enter your CRM command: ", async (command) => {
  try {
    const analysis = await analyzeCommand(command);
    console.log("Analysis:", analysis);

    const result = await executeCommand(analysis);
    console.log("Execution Result:", result);
  } catch (error) {
    console.error("Error executing command:", error.message);
  } finally {
    rl.close();
  }
});