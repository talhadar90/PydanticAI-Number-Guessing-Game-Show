import asyncio
import logging
from termcolor import colored
from agents.player_agent import PlayerAgent, PlayerState, GameHistory
from agents.referee_agent import RefereeAgent, GameRules
from agents.narrator_agent import NarratorAgent, GuessContext
from typing import Dict, Tuple
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class GameEngine:
    def __init__(self, config: dict):
        logger.info(colored("Initializing Number Guessing Game Show!", "cyan", attrs=["bold"]))
        self.players: Dict[str, PlayerState] = {}
        self.game_state = {
            'shared_valid_range': (1, 100),
            'secret_number': None,
            'last_guess': None,
            'current_turn': 0,
            'game_history': GameHistory()
        }
        
        logger.info("Initializing AI Agents")
        self.player_agent = PlayerAgent(
            model_name=config["model_name"],
            api_key=config["api_key"]
        )
        self.referee_agent = RefereeAgent(
            model_name=config["model_name"],
            api_key=config["api_key"]
        )
        self.narrator_agent = NarratorAgent(
            model_name=config["model_name"],
            api_key=config["api_key"]
        )
        self.game_rules = GameRules(min_number=1, max_number=100, max_tries_per_player=3)
        logger.info(colored("Game Show initialization complete!", "green"))

    def update_game_state(self, new_range: tuple[int, int], guess: int, narration: str):
        self.game_state['shared_valid_range'] = new_range
        self.game_state['last_guess'] = guess
        self.game_state['current_turn'] += 1
        self.game_state['game_history'].narrator_feedback.append(narration)
        
        for player in self.players.values():
            player.valid_range = new_range
            player.min_range = new_range[0]
            player.max_range = new_range[1]
            player.game_history = self.game_state['game_history']

    async def start_game(self, game_id: str, initial_state: dict) -> None:
        logger.info(colored("🎪 Starting new Number Guessing Game Show! 🎪", "cyan", attrs=["bold"]))
        
        for player_id, player_data in initial_state["players"].items():
            self.players[player_id] = PlayerState(
                player_id=player_id,
                previous_guesses=[],
                min_range=self.game_rules.min_number,
                max_range=self.game_rules.max_number,
                tries_remaining=self.game_rules.max_tries_per_player,
                valid_range=self.game_state['shared_valid_range'],
                game_history=self.game_state['game_history']
            )
        
        # Store the returned secret number in game state
        self.game_state['secret_number'] = await self.referee_agent.generate_secret_number(self.game_rules)
        logger.info(colored(f"🎲 Game Set! Secret Number: {self.game_state['secret_number']}", "red", attrs=["bold"]))


    async def process_guess(self, player_id: str) -> bool:
        player_state = self.players[player_id]
        
        if player_state.tries_remaining <= 0:
            logger.info(colored(f"Player {player_id} has no tries remaining!", "yellow"))
            return False
            
        logger.info(colored(f"\n{'='*50}\nPlayer {player_id}'s turn!", "blue", attrs=["bold"]))
        logger.info(f"Valid range: {self.game_state['shared_valid_range']}")

        # Share game history with player
        player_state.game_history = self.game_state['game_history']
        action = await self.player_agent.decide_action(player_state)
        
        if not self.validate_range(action.number, self.game_state['shared_valid_range']):
            logger.warning(colored(f"Invalid guess {action.number}!", "red"))
            return False

        logger.info(colored(f"Player {player_id} guesses: {action.number}!", "cyan"))

        # Referee validation
        guess_result = await self.referee_agent.validate_guess(
            action.number,
            self.game_rules,
            player_id
        )

        # Narration
        context = GuessContext(
            current_turn=self.game_state['current_turn'],
            player_id=player_id,
            guess=action.number,
            feedback=guess_result.feedback,
            previous_guesses=player_state.previous_guesses,
            is_winner=guess_result.is_correct,
            tries_remaining=player_state.tries_remaining - 1,
            valid_range=guess_result.valid_range
        )
        
        narration = await self.narrator_agent.narrate_guess(context)

        # Update game state with narration
        self.update_game_state(guess_result.valid_range, action.number, narration.description)
        
        # Update player state
        player_state.last_feedback = narration.description
        player_state.previous_guesses.append(action.number)
        player_state.attempts += 1
        player_state.tries_remaining -= 1

        print(colored("\n=== Game Show Update ===", "yellow", attrs=["bold"]))
        print(colored(narration.description, "green"))
        print(colored(f"Valid range: {self.game_state['shared_valid_range']}", "cyan"))
        print(f"{'='*50}\n")

        return guess_result.is_correct
    
    def validate_range(self, guess: int, current_range: Tuple[int, int]) -> bool:
        min_val, max_val = current_range
        return min_val <= guess <= max_val

    async def check_game_over(self) -> bool:
        return all(player.tries_remaining <= 0 for player in self.players.values())

async def main():
    logger.info("🎪 Welcome to the Number Guessing Game Show! 🎪")
    anthropic_config = {
        "model_name": os.getenv("ANTHROPIC_MODEL_NAME"),
        "api_key": os.getenv("ANTHROPIC_API_KEY")
    }
    
    engine = GameEngine(anthropic_config)
    game_id = "number_guess_1"
    initial_state = {
        "players": {
            "player1": {"name": "Contestant 1"},
            "player2": {"name": "Contestant 2"}
        }
    }

    await engine.start_game(game_id, initial_state)
    winner_found = False
    current_player = "player1"
    
    while not winner_found and not await engine.check_game_over():
        winner_found = await engine.process_guess(current_player)
        if not winner_found:
            current_player = "player2" if current_player == "player1" else "player1"

    if winner_found:
        logger.info(f"🎉 Congratulations! {current_player} won the game! 🎉")
    else:
        logger.info(f"🎭 Game Over! The secret number was {engine.game_state['secret_number']}! 🎭")

if __name__ == "__main__":
    asyncio.run(main())
