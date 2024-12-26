from typing import Union
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SecretNumber(BaseModel):
    number: int
    reasoning: str

class GuessResult(BaseModel):
    is_correct: bool
    feedback: str
    distance: str  # "higher", "lower", or "correct"
    valid_range: tuple[int, int]
    tries_remaining: int

class RuleViolation(BaseModel):
    violation_type: str
    description: str
    severity: int

class ActionValidation(BaseModel):
    is_valid: bool
    reason: str
    penalty: Optional[int] = None

@dataclass
class GameRules:
    min_number: int = 1
    max_number: int = 100
    max_attempts: int = 10
    allowed_actions: list[str] = ("guess",)
    turn_limits: dict[str, int] = None
    scoring_rules: dict[str, int] = None
    max_tries_per_player: int = 3

class RefereeAgent:
    def __init__(self, model_name: str, api_key: str):
        model = AnthropicModel(model_name, api_key=api_key)
        self.agent = Agent(
            model,
            deps_type=GameRules,
            result_type=Union[SecretNumber, GuessResult, RuleViolation],
            system_prompt="""You are the referee of a number guessing game.
            Your role is to:
            1. Choose a secret number and explain your choice
            2. Evaluate player guesses accurately
            3. Provide clear feedback on each guess
            4. Track valid ranges and remaining tries
            5. Declare winners when correct"""
        )
        self.secret_number = None
        self.valid_range = (1, 100)
        self.player_tries = {}

    async def generate_secret_number(self, rules: GameRules) -> int:
        result = await self.agent.run(
            f"Choose a secret number between {rules.min_number} and {rules.max_number}. Explain your choice.",
            deps=rules
        )
        secret = result.data
        self.secret_number = secret.number
        self.valid_range = (rules.min_number, rules.max_number)
        logger.info(f"🎯 SECRET NUMBER SET: {self.secret_number}")
        logger.info(f"Referee's reasoning: {secret.reasoning}")
        logger.info(f"Initial valid range: {self.valid_range}")
        return self.secret_number  # Return the secret number

    def update_range(self, guess: int) -> tuple[int, int]:
        min_val, max_val = self.valid_range
        if guess > self.secret_number:
            max_val = guess - 1
        elif guess < self.secret_number:
            min_val = guess + 1
        return (min_val, max_val)

    def get_tries_remaining(self, player_id: str) -> int:
        if player_id not in self.player_tries:
            self.player_tries[player_id] = 3
        return self.player_tries[player_id]

    async def validate_guess(self, guess: int, rules: GameRules, player_id: str) -> GuessResult:
        if not self.secret_number:
            await self.generate_secret_number(rules)

        tries_remaining = self.get_tries_remaining(player_id)
        if tries_remaining <= 0:
            return GuessResult(
                is_correct=False,
                feedback="No more tries remaining!",
                distance="none",
                valid_range=self.valid_range,
                tries_remaining=0
            )

        self.player_tries[player_id] -= 1
        tries_remaining = self.player_tries[player_id]
        
        if guess == self.secret_number:
            return GuessResult(
                is_correct=True,
                feedback=f"🎉 Correct! The secret number was {self.secret_number}",
                distance="correct",
                valid_range=self.valid_range,
                tries_remaining=tries_remaining
            )

        self.valid_range = self.update_range(guess)
        distance = "lower" if guess > self.secret_number else "higher"
        feedback = f"The secret number is {distance} than {guess}"
        
        logger.info(f"Updated valid range: {self.valid_range}")
        logger.info(f"Player {player_id} has {tries_remaining} tries remaining")

        return GuessResult(
            is_correct=False,
            feedback=feedback,
            distance=distance,
            valid_range=self.valid_range,
            tries_remaining=tries_remaining
        )

    async def validate_action(self, action: dict, rules: GameRules) -> Union[ActionValidation, RuleViolation]:
        if action.get("type") != "guess":
            return RuleViolation(
                violation_type="invalid_action",
                description="Only guess actions are allowed",
                severity=1
            )

        guess = action.get("number")
        if not isinstance(guess, int):
            return RuleViolation(
                violation_type="invalid_guess",
                description="Guess must be a number",
                severity=1
            )

        min_val, max_val = self.valid_range
        if guess < min_val or guess > max_val:
            return RuleViolation(
                violation_type="invalid_range",
                description=f"Guess must be within current valid range {self.valid_range}",
                severity=1
            )

        return ActionValidation(
            is_valid=True,
            reason="Valid guess attempt",
            penalty=None
        )
