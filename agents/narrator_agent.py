from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from dataclasses import dataclass
from typing import List, Optional

class NarrationResponse(BaseModel):
    description: str
    highlights: list[str]
    atmosphere: str
    suspense_level: int = 1
    tries_remaining: Optional[int] = None

@dataclass
class GuessContext:
    current_turn: int
    player_id: str
    guess: int
    feedback: str
    previous_guesses: List[int]
    is_winner: bool = False
    tries_remaining: int = 3
    valid_range: tuple[int, int] = (1, 100)

class NarratorAgent:
    def __init__(self, model_name: str, api_key: str):
        model = AnthropicModel(model_name, api_key=api_key)
        self.agent = Agent(
            model,
            deps_type=GuessContext,
            result_type=NarrationResponse,
            system_prompt="""You are the charismatic host of an exciting number guessing game show!

            Your style should:
            1. Build suspense around each guess
            2. Create excitement when players get close
            3. Use game show catchphrases and dramatic pauses
            4. Maintain high energy throughout
            5. Make each guess feel consequential
            6. Emphasize remaining tries
            7. Reference the valid number range

            Examples:
            - "With only 2 tries left, Player 1 steps up boldly to the podium!"
            - "The number must be between 45 and 60! Can they crack the code?"
            - "The crowd holds their breath as we await the next strategic guess!"
            """
        )

    async def narrate_guess(self, context: GuessContext) -> NarrationResponse:
        if context.is_winner:
            return await self._narrate_victory(context)
        if context.tries_remaining <= 0:
            return await self._narrate_game_over(context)

        prompt = (
            f"Narrate this dramatic moment:\n"
            f"- Player {context.player_id} guesses {context.guess}\n"
            f"- Valid range: {context.valid_range}\n"
            f"- Tries remaining: {context.tries_remaining}\n"
            f"- Feedback: {context.feedback}\n"
            f"- Turn number: {context.current_turn}\n"
            f"- Previous guesses: {context.previous_guesses}"
        )
        result = await self.agent.run(prompt, deps=context)
        return result.data

    async def _narrate_victory(self, context: GuessContext) -> NarrationResponse:
        prompt = (
            f"Create an epic victory narration for correctly guessing the secret number:\n"
            f"- Champion: Player {context.player_id}\n"
            f"- Winning number: {context.guess}\n"
            f"- Journey: {context.previous_guesses}\n"
            f"- Tries remaining: {context.tries_remaining}\n"
            "Make it spectacular and celebratory!"
        )
        result = await self.agent.run(prompt, deps=context)
        return result.data

    async def _narrate_game_over(self, context: GuessContext) -> NarrationResponse:
        prompt = (
            f"Create a dramatic game over narration:\n"
            f"- Player {context.player_id}\n"
            f"- Last guess: {context.guess}\n"
            f"- Valid range was: {context.valid_range}"
        )
        result = await self.agent.run(prompt, deps=context)
        return result.data

    def generate_suspense_line(self, context: GuessContext) -> str:
        if context.tries_remaining == 1:
            return "This is it! The final try! Can they pull off a miracle?"
        if len(context.previous_guesses) > 3:
            return f"The tension is electric as Player {context.player_id} narrows down the possibilities!"
        return f"With {context.tries_remaining} tries remaining, who will crack the code first?"
