
# Rasa Assistant

This is your Rasa assistant project. Below are the basic commands to
get started.

## Prerequisites
Make sure you have [uv](https://docs.astral.sh/uv/) installed.

## Training the Assistant

To train your assistant with the current configuration and training data:

```bash
uv run rasa train
```

This will create a model in the `models/` directory.

## Testing the Assistant

To test your assistant interactively in the command line:

```bash
uv run rasa inspect
```

## Running the Assistant

To start the Rasa server:

```bash
uv run rasa run
```

The server will be available at `http://localhost:5005`.

## Project Structure

- `config.yml` - Configuration for your NLU pipeline and policies
- `domain.yml` - Defines intents, entities, slots, responses, and actions
- `data/` - Flows of your bot
- `actions/` - Custom action code (if any)

## Next Steps

1. Customize your domain and flows
2. Train your model with `rasa train`
3. Test your assistant with `rasa inspect`
4. Deploy your assistant with `rasa run`

For more information, visit the [Rasa documentation](https://rasa.com/docs/).
