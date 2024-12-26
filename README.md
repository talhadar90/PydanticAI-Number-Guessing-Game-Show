# PydanticAI Number Guessing Game Show

An exciting multiplayer number guessing game powered by PydanticAI using the Anthropic Claude API. 

Watch AI players compete in a thrilling game show atmosphere!

## Getting Started

### Prerequisites
- Python 3.11+
- Anthropic API key

### Installation

1. Clone the repository
```bash
git clone [https://github.com/yourusername/ai-number-guessing-game.git](https://github.com/talhadar90/PydanticAI-Number-Guessing-Game-Show)
```

2. Install requirements.txt
```bash
pip install -r requirements.txt
```

3. Update .env
```bash
ANTHROPIC_MODEL_NAME=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=add-your-api
```

4. Run
```
python main.py
```

## Game Rules
- AI players take turns guessing a secret number between 1-100
- Each player gets 3 attempts
- The referee provides feedback after each guess
- Valid ranges update dynamically
- First player to guess correctly wins!

## PydancticAI Docs
https://ai.pydantic.dev/
