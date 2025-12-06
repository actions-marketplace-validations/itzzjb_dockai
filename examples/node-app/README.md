# DockAI Node Example

A tiny Express server you can use to see DockAI generate a Dockerfile for a Node.js app.

## Run the app locally

```bash
cd examples/node-app
npm install
npm start
```

The server listens on `PORT` (default 3000) with two routes:
- `/` returns JSON: `{ "message": "Hello from DockAI Node example" }`
- `/health` returns `ok`

## Use DockAI to generate a Dockerfile

1) Install DockAI (requires Python 3.10+ and Docker):

```bash
pip install dockai-cli
```

2) Set your LLM provider credentials (example with OpenAI):

```bash
export OPENAI_API_KEY="sk-your-key"
# Optional: DOCKAI_LLM_PROVIDER=openai|gemini|anthropic|ollama|azure
```

3) From the repo root, ask DockAI to build a Dockerfile for this project:

```bash
dockai build examples/node-app --verbose
```

DockAI will scan the Node app, plan a containerization strategy, and write a `Dockerfile` inside `examples/node-app/`.

4) Build and run the generated image (after DockAI creates the Dockerfile):

```bash
cd examples/node-app
npm install  # ensure dependencies present for the image build
docker build -t dockai-node-example:local .
docker run --rm -p 3000:3000 dockai-node-example:local
```

Visit http://localhost:3000 to verify the containerized app.

### Tips
- Add a `.env` file at the repo root (or export vars) to persist your DockAI credentials.
- To prefer small images, you can set `DOCKAI_GENERATOR_INSTRUCTIONS="Use slim or alpine where safe"` when running `dockai build`.
