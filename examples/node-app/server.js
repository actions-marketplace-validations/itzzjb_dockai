const express = require('express');

const app = express();
const port = process.env.PORT || 3000;

app.get('/', (_req, res) => {
  res.json({ message: 'Hello from DockAI Node example' });
});

app.get('/health', (_req, res) => {
  res.status(200).send('ok');
});

app.listen(port, () => {
  console.log(`Server listening on http://localhost:${port}`);
});
