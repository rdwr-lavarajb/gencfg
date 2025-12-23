# Environment Setup

## OpenAI API Key Configuration

Phase 2 requires an OpenAI API key for semantic analysis. The key should be stored in a `.env` file which is **not committed to git**.

### Setup Steps

1. **Run the setup script:**
   ```bash
   python setup_env.py
   ```

2. **Get your OpenAI API key:**
   - Go to: https://platform.openai.com/api-keys
   - Create a new API key
   - Copy the key (starts with `sk-...`)

3. **Edit the `.env` file:**
   ```bash
   # Open in your editor
   notepad .env    # Windows
   # or
   code .env       # VS Code
   ```

4. **Add your key:**
   ```env
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   ```

5. **Save and verify:**
   ```bash
   python setup_env.py
   ```

### File Structure

```
.env.example      # Template (committed to git)
.env              # Your actual keys (gitignored)
```

### Security Notes

- ✅ `.env` is in `.gitignore` - your key will NOT be committed
- ✅ Never hardcode API keys in source code
- ✅ Never commit `.env` files to version control
- ✅ Use `.env.example` as a template for team members

### Testing Without API Key

If you don't have an API key yet, the code will gracefully handle it:
- Phase 2 components will use fallback logic
- Tests will skip AI calls
- You can still test other functionality

### Cost Estimation

OpenAI GPT-4 usage for this project:
- ~$2.50 per full processing run (27 modules)
- Costs are logged during processing
- See `docs/PHASE2_DESIGN.md` for details
