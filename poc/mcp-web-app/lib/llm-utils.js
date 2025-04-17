const axios = require('axios');
require('dotenv').config();

async function askLLM(prompt, model = 'claude') {
  if (model === 'claude') {
    const response = await axios.post('https://api.anthropic.com/v1/messages', {
      model: 'claude-3-opus-20240229',
      max_tokens: 2048,
      messages: [{ role: 'user', content: prompt }]
    }, {
      headers: {
        'x-api-key': process.env.CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
      }
    });

    return response.data.content;
  }

  throw new Error(`Unsupported LLM model: ${model}`);
}

module.exports = { askLLM };
