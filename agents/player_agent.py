from typing import Optional, List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class GameHistory(BaseModel):
    narrator_feedback: List[str] = []
    other_player_guesses: List[int] = []
    game_commentary: List[str] = []

class PlayerAction(BaseModel):
    action_type: str = "guess"
    number: int
    confidence: Optional[float]
    reasoning: str

@dataclass
class PlayerState:
    player_id: str
    min_range: int = 1
    max_range: int = 100
    previous_guesses: list[int] = None
    last_feedback: str = None
    attempts: int = 0
    valid_range: tuple[int, int] = (1, 100)
    tries_remaining: int = 3
    game_history: GameHistory = None

class PlayerAgent:
    def __init__(self, model_name: str, api_key: str):
        model = AnthropicModel(model_name, api_key=api_key)
        self.agent = Agent(
            model,
            deps_type=PlayerState,
            result_type=PlayerAction,
            system_prompt="""You are a strategic player in a number guessing game show.
            
Your role is to:
1. Use binary search strategy
2. Track valid number ranges precisely
3. Never repeat previous guesses or other player's guesses
4. Make optimal guesses based on all available feedback
5. Learn from narrator commentary and game history

When making a guess:
- Consider narrator's feedback and game commentary
- Avoid numbers already guessed by any player
- Use binary search within valid range
- Factor in remaining tries
- Provide strategic reasoning for your choice"""
        )
        self.game_history = GameHistory()
        self.previous_guesses = []
        self.valid_range = (1, 100)
        self.tries_remaining = 3

    def update_game_history(self, narrator_feedback: str, other_guess: int = None):
        if narrator_feedback:
            self.game_history.narrator_feedback.append(narrator_feedback)
        if other_guess:
            self.game_history.other_player_guesses.append(other_guess)

    def get_optimal_guess(self, state: PlayerState) -> int:
        min_val, max_val = state.valid_range
        all_guesses = self.previous_guesses + self.game_history.other_player_guesses
        remaining_numbers = [
            n for n in range(min_val, max_val + 1)
            if n not in all_guesses
        ]
        if not remaining_numbers:
            return min_val
        return remaining_numbers[len(remaining_numbers) // 2]

    async def decide_action(self, state: PlayerState) -> PlayerAction:
        self.tries_remaining = state.tries_remaining
        if self.tries_remaining <= 0:
            return PlayerAction(
                action_type="forfeit",
                number=0,
                confidence=0,
                reasoning="No more tries remaining"
            )

        if state.last_feedback:
            self.update_game_history(state.last_feedback)

        next_guess = self.get_optimal_guess(state)
        guess_prompt = f"""
        Game State Analysis:
        - Valid range: {state.valid_range}
        - Your previous guesses: {self.previous_guesses}
        - Other player's guesses: {self.game_history.other_player_guesses}
        - Recent narrator feedback: {self.game_history.narrator_feedback[-3:] if self.game_history.narrator_feedback else 'None'}
        - Tries remaining: {self.tries_remaining}

        Based on all available information, explain why {next_guess} is the optimal next guess.
        """
        result = await self.agent.run(guess_prompt, deps=state)
        action = result.data
        action.number = next_guess
        action.confidence = 1.0 / (len(self.previous_guesses) + 1)
        
        logger.info(f"Player {state.player_id} analysis:")
        logger.info(f"Valid range: {state.valid_range}")
        logger.info(f"Game history considered: {len(self.game_history.narrator_feedback)} narrator updates")
        logger.info(f"Reasoning: {action.reasoning}")
        
        self.previous_guesses.append(next_guess)
        return action
    
    def update_range(self, guess: int, feedback: str):
        min_val, max_val = self.valid_range
        if "higher" in feedback.lower():
            min_val = max(min_val, guess + 1)
        elif "lower" in feedback.lower():
            max_val = min(max_val, guess - 1)
        self.valid_range = (min_val, max_val)
        logger.info(f"Player range updated to: {self.valid_range}")

