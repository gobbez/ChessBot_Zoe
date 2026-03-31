"""
Zoe Chess Bot - Revisited 2026 Edition

A Lichess chess bot powered by Stockfish with Telegram integration.
This is a refactored and improved version with better organization,
type safety, and configuration management.

Quick Start:
    1. Configure config.yml with your tokens
    2. Ensure Stockfish binaries are in place
    3. Run: python revisited2026.py

Author: Original by ChessBot_Zoe Team
Refactored: 2026 Edition
"""

from __future__ import annotations

import asyncio
import platform
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import berserk
import chess
import chess.engine
import chess.pgn
import chess.variant
import pandas as pd
import yaml

import run_telegram_bot

# Avoid max recursion limit
sys.setrecursionlimit(100_000)

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class EngineConfig:
    """Stockfish engine configuration."""
    deep_time: float
    skill_level: int
    hash_memory: int  # in MB
    depth: int
    threads: int


@dataclass
class BotSettings:
    """Global bot settings loaded from database."""
    level: int = 20
    think: float = 10.0
    hash_memory: int = 2056
    depth: int = 25
    threads: int = 18
    wait_api: int = 10
    challenge_loops: int = 2000
    challenge_time: int = 900
    challenge_increment: int = 14
    challenge_opponent_elo: int = 3000
    challenge_variant: str = "standard"


@dataclass(frozen=True)
class Paths:
    """Application paths."""
    base: Path = Path(__file__).parent.resolve()

    @property
    def config(self) -> Path:
        return self.base / "config.yml"

    @property
    def database_dir(self) -> Path:
        return self.base / "database"

    @property
    def settings_csv(self) -> Path:
        return self.database_dir / "Settings.csv"

    @property
    def chat_csv(self) -> Path:
        return self.database_dir / "AIChat.csv"

    @property
    def stockfish(self) -> Path:
        """Returns the appropriate Stockfish binary path based on OS."""
        if platform.system() == "Windows":
            return self.base / "stockfish" / "stockfish-windows-x86-64-avx2.exe"
        return self.base / "stockfish" / "stockfish-ubuntu-x86-64-avx2"

    @property
    def fairy_stockfish(self) -> Path:
        """Returns the appropriate Fairy-Stockfish binary path based on OS."""
        if platform.system() == "Windows":
            return (
                self.base / "stockfish" / "Fairy" / "Windows"
                / "fairy-stockfish-largeboard_x86-64-bmi2.exe"
            )
        return (
            self.base / "stockfish" / "Fairy" / "Linux"
            / "fairy-stockfish-largeboard_x86-64-bmi2"
        )


# =============================================================================
# CONSTANTS
# =============================================================================

class ChessVariant(Enum):
    """Supported chess variants."""
    STANDARD = "standard"
    CHESS960 = "chess960"
    FROM_POSITION = "fromPosition"
    CRAZYHOUSE = "crazyhouse"
    ANTICHESS = "antichess"
    ATOMIC = "atomic"
    HORDE = "horde"
    KING_OF_THE_HILL = "kingOfTheHill"
    RACING_KINGS = "racingKings"
    THREE_CHECK = "threeCheck"

    @classmethod
    def from_string(cls, variant: str) -> ChessVariant:
        """Get variant from string, defaulting to STANDARD."""
        try:
            return cls(variant)
        except ValueError:
            return cls.STANDARD


# Variant to board class mapping
VARIANT_BOARD_MAP: dict[ChessVariant, type[chess.Board]] = {
    ChessVariant.STANDARD: chess.Board,
    ChessVariant.CHESS960: chess.Board,
    ChessVariant.FROM_POSITION: chess.Board,
    ChessVariant.CRAZYHOUSE: chess.variant.CrazyhouseBoard,
    ChessVariant.ANTICHESS: chess.variant.AntichessBoard,
    ChessVariant.ATOMIC: chess.variant.AtomicBoard,
    ChessVariant.HORDE: chess.variant.HordeBoard,
    ChessVariant.KING_OF_THE_HILL: chess.variant.KingOfTheHillBoard,
    ChessVariant.RACING_KINGS: chess.variant.RacingKingsBoard,
    ChessVariant.THREE_CHECK: chess.variant.ThreeCheckBoard,
}

# ELO-based engine configurations
ELO_CONFIGS: list[tuple[int, EngineConfig]] = [
    (700, EngineConfig(0.2, 2, 16, 4, 4)),
    (1000, EngineConfig(0.5, 4, 16, 8, 8)),
    (1500, EngineConfig(1.0, 9, 32, 10, 11)),
    (2000, EngineConfig(1.5, 14, 128, 12, 11)),
    (2300, EngineConfig(2.3, 16, 512, 15, 13)),
    (2500, EngineConfig(5.0, 18, 1028, 20, 15)),
    (99999, EngineConfig(10.0, 20, 2056, 25, 18)),  # Default for >2500
]

# Challenge settings
MIN_CHALLENGE_TIME = 180
DEFAULT_CHALLENGE_TIME = 900
MIN_CHALLENGE_INCREMENT = 0
DEFAULT_CHALLENGE_INCREMENT = 14
MIN_CHALLENGE_ELO = 0
DEFAULT_CHALLENGE_ELO = 3000

# Game settings
FAST_GAME_THRESHOLD = 120  # seconds
FAST_GAME_CONFIG = EngineConfig(1.0, 20, 2000, 15, 12)

# Evaluation CP thresholds for adaptive play
CP_THRESHOLDS = {
    "winning": 800,
    "advantage": 600,
    "moderate": 400,
    "equal": 100,
    "slight": 50,
}

# Telegram retry settings
MAX_CHALLENGE_RETRIES = 3
RATE_LIMIT_WAIT = 10  # seconds


# =============================================================================
# SETTINGS DATABASE MANAGER
# =============================================================================

class SettingsDB:
    """
    Manages the global settings database (CSV file).
    Thread-safe singleton for accessing and modifying bot settings.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._lock = threading.Lock()

    def _load(self) -> pd.DataFrame:
        """Load the settings DataFrame."""
        return pd.read_csv(self._csv_path)

    def _save(self, df: pd.DataFrame) -> None:
        """Save the settings DataFrame."""
        df.to_csv(self._csv_path, index=False)

    def get(self, setting_name: str, game: str = "global") -> Any:
        """
        Get a setting value from the database.

        Args:
            setting_name: Name of the setting (e.g., 'level', 'think')
            game: Game identifier (default: 'global')

        Returns:
            The setting value or None if not found
        """
        with self._lock:
            df = self._load()
            row = df[df["Game"] == game]

            if len(row) != 1:
                return None

            column_map = {
                "level": "Level",
                "think": "Think",
                "hash": "Hash",
                "depth": "Depth",
                "thread": "Thread",
                "wait_api": "Wait_Api",
                "challenge_loops": "Challenge_Loops",
                "challenge_time": "Challenge_Time",
                "challenge_increment": "Challenge_Increment",
                "challenge_opp_elo": "Challenge_Opponent_Elo",
                "challenge_variant": "Challenge_Variant",
            }

            column = column_map.get(setting_name)
            if column and column in row.columns:
                return row.iloc[0][column]
            return None

    def set(self, setting_name: str, value: Any, game: str = "global") -> None:
        """
        Set a setting value in the database.

        Args:
            setting_name: Name of the setting to modify
            value: New value to set
            game: Game identifier (default: 'global')
        """
        with self._lock:
            df = self._load()

            column_map = {
                "level": "Level",
                "think": "Think",
                "hash": "Hash",
                "depth": "Depth",
                "thread": "Thread",
                "wait_api": "Wait_Api",
                "challenge_loops": "Challenge_Loops",
                "challenge_time": "Challenge_Time",
                "challenge_increment": "Challenge_Increment",
                "challenge_opp_elo": "Challenge_Opponent_Elo",
                "challenge_variant": "Challenge_Variant",
            }

            column = column_map.get(setting_name)
            if column:
                df.loc[df["Game"] == game, column] = value
                self._save(df)

    def get_all_settings(self) -> BotSettings:
        """Load all settings into a BotSettings object."""
        return BotSettings(
            level=self.get("level") or 20,
            think=self.get("think") or 10.0,
            hash_memory=self.get("hash") or 2056,
            depth=self.get("depth") or 25,
            threads=self.get("thread") or 18,
            wait_api=self.get("wait_api") or 10,
            challenge_loops=self.get("challenge_loops") or 2000,
            challenge_time=self.get("challenge_time") or 900,
            challenge_increment=self.get("challenge_increment") or 14,
            challenge_opponent_elo=self.get("challenge_opp_elo") or 3000,
            challenge_variant=self.get("challenge_variant") or "standard",
        )


# =============================================================================
# CHAT DATABASE
# =============================================================================

class ChatDB:
    """Manages the chat message database for AI-generated messages."""

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._messages: list[str] = []
        self._load()

    def _load(self) -> None:
        """Load messages from CSV."""
        try:
            df = pd.read_csv(self._csv_path)
            self._messages = df["Intro_message"].tolist()
        except Exception as e:
            print(f"Warning: Could not load chat database: {e}")
            self._messages = ["Hello! Good luck! 👋"]

    def get_random_message(self) -> str:
        """Return a random chat message."""
        if not self._messages:
            return "Hello! Good luck! 👋"
        return random.choice(self._messages)


# =============================================================================
# CHESS ENGINE MANAGER
# =============================================================================

class ChessEngine:
    """
    Manages Stockfish engine interactions.
    Handles position evaluation and move calculation with adaptive strength.
    """

    def __init__(self, paths: Paths, settings_db: SettingsDB, telegram_token: str) -> None:
        self._paths = paths
        self._settings_db = settings_db
        self._telegram_token = telegram_token

    def _get_engine_path(self, variant: ChessVariant) -> Path:
        """Get the appropriate engine path for the variant."""
        if variant in (ChessVariant.STANDARD, ChessVariant.CHESS960, ChessVariant.FROM_POSITION):
            return self._paths.stockfish
        return self._paths.fairy_stockfish

    def _create_board(self, fen: str, variant: ChessVariant) -> chess.Board:
        """Create the appropriate board for the variant."""
        board_class = VARIANT_BOARD_MAP.get(variant, chess.Board)
        return board_class(fen)

    def _get_elo_config(self, elo: int) -> EngineConfig:
        """Get engine configuration based on opponent ELO."""
        for max_elo, config in ELO_CONFIGS:
            if elo <= max_elo:
                return config
        return ELO_CONFIGS[-1][1]

    def evaluate_position(self, fen: str, variant: ChessVariant) -> int:
        """
        Analyze the position and return centipawn value.

        Args:
            fen: FEN position string
            variant: Chess variant

        Returns:
            Centipawn evaluation (positive = advantage for side to move)
        """
        path = self._get_engine_path(variant)
        board = self._create_board(fen, variant)

        with chess.engine.SimpleEngine.popen_uci(path) as engine:
            info = engine.analyse(board, chess.engine.Limit(time=2.0))
            score_str = str(info["score"].relative)

            # Handle mate scores
            if "#" in score_str:
                mate_moves = int(score_str.replace("#", ""))
                return mate_moves * 1000

            return int(score_str)

    def _calculate_elo_strength(self, config: EngineConfig) -> float:
        """Calculate estimated ELO strength based on parameters."""
        return (
            (config.skill_level / 20 +
             config.hash_memory / 3000 +
             config.depth / 30 +
             config.threads / 12 +
             config.deep_time / 20) / 5 * 3200
        )

    def _apply_cp_adjustments(
        self, config: EngineConfig, cp: int
    ) -> EngineConfig:
        """Apply adjustments based on position evaluation."""
        # Start with a copy of base values
        deep_time = config.deep_time
        skill_level = config.skill_level
        hash_memory = config.hash_memory
        depth = config.depth
        threads = config.threads

        # Apply adjustments based on CP evaluation
        if cp > CP_THRESHOLDS["winning"]:
            skill_level = 20
        elif CP_THRESHOLDS["moderate"] < cp <= CP_THRESHOLDS["advantage"]:
            deep_time *= 0.5
            skill_level -= 4
            hash_memory = int(hash_memory * 0.7)
            depth = int(depth * 0.6)
            threads = int(threads * 0.7)
        elif CP_THRESHOLDS["equal"] < cp <= CP_THRESHOLDS["moderate"]:
            deep_time *= 0.7
            skill_level -= 3
            hash_memory = int(hash_memory * 0.8)
            depth = int(depth * 0.8)
            threads = int(threads * 0.8)
        elif CP_THRESHOLDS["slight"] < cp <= CP_THRESHOLDS["equal"]:
            deep_time *= 0.8
            skill_level -= 2
            hash_memory = int(hash_memory * 0.9)
            depth = int(depth * 0.9)
            threads = int(threads * 0.9)
        elif 0 < cp <= CP_THRESHOLDS["slight"]:
            deep_time *= 0.9
            skill_level -= 1
        elif -CP_THRESHOLDS["slight"] < cp < 0:
            deep_time *= 1.1
            skill_level += 1
        elif -CP_THRESHOLDS["equal"] < cp <= -CP_THRESHOLDS["slight"]:
            deep_time *= 1.4
            skill_level += 2
            hash_memory = int(hash_memory * 1.05 + 50)
        elif -CP_THRESHOLDS["moderate"] < cp <= -CP_THRESHOLDS["equal"]:
            deep_time *= 2.0
            skill_level += 3
            hash_memory = int(hash_memory * 1.1 + 100)
            threads = int(threads * 1.1)
        elif -CP_THRESHOLDS["advantage"] < cp <= -CP_THRESHOLDS["moderate"]:
            deep_time *= 4.0
            skill_level += 5
            hash_memory = int(hash_memory * 1.3 + 200)
            threads = int(threads * 1.2)
        elif cp <= -CP_THRESHOLDS["advantage"]:
            deep_time *= 7.0
            skill_level = 20
            hash_memory = int(hash_memory * 1.5 + 300)
            threads = int(threads * 1.4)

        # Clamp values
        skill_level = max(1, min(20, skill_level))
        threads = min(12, threads)

        return EngineConfig(deep_time, skill_level, hash_memory, depth, threads)

    def _apply_global_overrides(self, config: EngineConfig) -> EngineConfig:
        """Apply global settings overrides from Telegram/database."""
        deep_time = config.deep_time
        skill_level = config.skill_level
        hash_memory = config.hash_memory
        depth = config.depth
        threads = config.threads

        # Check global overrides
        set_level = self._settings_db.get("level")
        if set_level is not None and 0 < set_level <= 20:
            skill_level = set_level
        elif set_level is not None and set_level < 0:
            skill_level = 1

        set_think = self._settings_db.get("think")
        if set_think is not None and set_think > 0:
            deep_time = min(3600, set_think)

        set_hash = self._settings_db.get("hash")
        if set_hash is not None and set_hash > 0:
            hash_memory = min(5100, set_hash)

        set_depth = self._settings_db.get("depth")
        if set_depth is not None and set_depth > 0:
            depth = min(50, set_depth)

        set_thread = self._settings_db.get("thread")
        if set_thread is not None and set_thread > 0:
            threads = min(12, set_thread)

        return EngineConfig(deep_time, skill_level, hash_memory, depth, threads)

    def get_best_move(
        self,
        fen: str,
        opponent_elo: int,
        opponent_name: str,
        game_id: str,
        variant: ChessVariant,
        is_fast_game: bool = False,
    ) -> tuple[chess.Move, float]:
        """
        Get the best move for the current position.

        Args:
            fen: Current position FEN
            opponent_elo: Opponent's ELO rating
            opponent_name: Opponent's username
            game_id: Lichess game ID
            variant: Chess variant
            is_fast_game: Whether this is a fast game (< 2 min)

        Returns:
            Tuple of (best move, estimated ELO strength)
        """
        path = self._get_engine_path(variant)
        board = self._create_board(fen, variant)

        if is_fast_game:
            # Use fast game configuration
            config = FAST_GAME_CONFIG
            elo_strength = self._calculate_elo_strength(config)
        else:
            # Standard adaptive play
            cp = self.evaluate_position(fen, variant)
            base_config = self._get_elo_config(opponent_elo)

            # Apply CP-based adjustments
            adjusted_config = self._apply_cp_adjustments(base_config, cp)

            # Apply global overrides
            config = self._apply_global_overrides(adjusted_config)

            elo_strength = self._calculate_elo_strength(config)

            # Send info message to Telegram
            message = (
                f"Playing against: {opponent_name} -- {opponent_elo}\n"
                f"CP evaluation: {cp // 100}\n"
                f"Playing at level: {config.skill_level}\n"
                f"Thinking time: {round(config.deep_time, 1)}s\n"
                f"Hash Memory: {round(config.hash_memory)}Mb\n"
                f"Moves Depth: {round(config.depth)}\n"
                f"Threads Num: {round(config.threads)}\n"
                f"Playing at: {round(elo_strength)} Elo\n"
                f"Variant: {variant.value}"
            )
            run_telegram_bot.send_message_to_telegram(
                self._telegram_token, message
            )

        # Execute engine
        with chess.engine.SimpleEngine.popen_uci(path) as engine:
            engine.configure({"Hash": config.hash_memory})
            engine.configure({"Threads": config.threads})
            engine.configure({"Skill Level": config.skill_level})

            result = engine.play(
                board,
                chess.engine.Limit(time=config.deep_time, depth=config.depth)
            )

        return result.move, round(elo_strength)


# =============================================================================
# LICHESS CLIENT MANAGER
# =============================================================================

class LichessClient:
    """Manages Lichess API connections and operations."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize Lichess API clients."""
        # Main client for playing
        session = berserk.TokenSession(self._config["token"])
        self.client = berserk.Client(session=session)

        # Challenges client for reading challenges
        challenges_session = berserk.TokenSession(self._config["challenges_token"])
        self.challenges_client = berserk.Client(session=challenges_session)

    def get_ongoing_games(self) -> list[dict]:
        """Get list of ongoing games."""
        return self.client.games.get_ongoing()

    def stream_game_state(self, game_id: str):
        """Stream game state events."""
        return self.client.bots.stream_game_state(game_id)

    def make_move(self, game_id: str, uci_move: str) -> None:
        """Make a move in a game."""
        self.client.bots.make_move(game_id, uci_move)

    def post_message(self, game_id: str, message: str, spectator: bool = False) -> None:
        """Post a message to game chat."""
        self.client.bots.post_message(game_id, message, spectator)

    def accept_challenge(self, challenge_id: str) -> None:
        """Accept a challenge."""
        self.client.bots.accept_challenge(challenge_id)

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> None:
        """Decline a challenge."""
        self.client.bots.decline_challenge(challenge_id, reason)

    def create_challenge(
        self,
        username: str,
        rated: bool,
        clock_limit: int,
        clock_increment: int,
        variant: str = "standard",
    ) -> None:
        """Create a challenge against a user."""
        self.client.challenges.create(
            username=username,
            rated=rated,
            clock_limit=clock_limit,
            clock_increment=clock_increment,
            variant=variant,
        )

    def get_online_bots(self) -> list[dict]:
        """Get list of online bots."""
        return self.client.bots.get_online_bots()

    def get_my_challenges(self) -> dict:
        """Get my pending challenges."""
        return self.challenges_client.challenges.get_mine()


# =============================================================================
# GAME HANDLER
# =============================================================================

class GameHandler:
    """Handles individual game logic and move processing."""

    def __init__(
        self,
        lichess: LichessClient,
        engine: ChessEngine,
        chat_db: ChatDB,
        telegram_token: str,
    ) -> None:
        self._lichess = lichess
        self._engine = engine
        self._chat_db = chat_db
        self._telegram_token = telegram_token
        self._sent_welcome: set[str] = set()  # Track games where welcome was sent

    def _create_board(self, fen: str, variant: ChessVariant) -> chess.Board:
        """Create the appropriate board for the variant."""
        board_class = VARIANT_BOARD_MAP.get(variant, chess.Board)
        return board_class(fen)

    def _send_welcome_message(self, game_id: str) -> None:
        """Send a random welcome message if not already sent."""
        if game_id not in self._sent_welcome:
            message = self._chat_db.get_random_message()
            self._lichess.post_message(game_id, message, False)
            self._sent_welcome.add(game_id)

    def handle_turn(
        self,
        game_id: str,
        fen: str,
        opponent_elo: int,
        opponent_name: str,
        variant: ChessVariant,
        is_fast_game: bool = False,
    ) -> None:
        """
        Handle the bot's turn in a game.

        Args:
            game_id: Lichess game ID
            fen: Current position FEN
            opponent_elo: Opponent's ELO rating
            opponent_name: Opponent's username
            variant: Chess variant
            is_fast_game: Whether this is a fast game
        """
        board = self._create_board(fen, variant)

        try:
            # Get best move from engine
            next_move, elo_strength = self._engine.get_best_move(
                fen, opponent_elo, opponent_name, game_id, variant, is_fast_game
            )

            # Make the move
            self._lichess.make_move(game_id, next_move.uci())
            board.push(next_move)

            print(f"Move played: {next_move.uci()} (Stockfish @ {elo_strength} ELO)")

            # Send confirmation to game chat
            if not is_fast_game:
                message = f"My move is from Stockfish 17 at {elo_strength} ELO"
                self._lichess.post_message(game_id, message, False)

        except Exception as e:
            print(f"Engine error: {e}, playing random move")

            # Fallback to random move
            legal_moves = list(board.legal_moves)
            if legal_moves:
                random_move = random.choice(legal_moves)
                self._lichess.make_move(game_id, random_move.uci())
                board.push(random_move)

                # Notify via Telegram
                error_msg = f"Random move played in game {game_id}: {e}"
                run_telegram_bot.send_message_to_telegram(
                    self._telegram_token, error_msg
                )


# =============================================================================
# CHALLENGE MANAGER
# =============================================================================

class ChallengeManager:
    """Manages sending and accepting challenges."""

    def __init__(
        self,
        lichess: LichessClient,
        settings_db: SettingsDB,
        telegram_token: str,
    ) -> None:
        self._lichess = lichess
        self._settings_db = settings_db
        self._telegram_token = telegram_token
        self._retry_count = 0

    def send_bot_challenge(self) -> bool:
        """
        Send a challenge to a random high-rated bot.

        Returns:
            True if challenge was sent, False otherwise
        """
        if self._retry_count >= MAX_CHALLENGE_RETRIES:
            print("Max challenge retries reached")
            return False

        try:
            settings = self._settings_db.get_all_settings()

            # Validate and set defaults
            challenge_time = max(MIN_CHALLENGE_TIME, settings.challenge_time)
            challenge_increment = max(MIN_CHALLENGE_INCREMENT, settings.challenge_increment)
            challenge_elo = max(MIN_CHALLENGE_ELO, settings.challenge_opponent_elo)

            print(f"Searching for bots with ELO >= {challenge_elo}")

            # Get online bots
            online_bots = self._lichess.get_online_bots()
            eligible_bots = []

            for bot in online_bots:
                try:
                    rating = bot["perfs"]["classical"]["rating"]
                    if rating >= challenge_elo:
                        eligible_bots.append(bot["username"])
                except (KeyError, TypeError):
                    continue

            if not eligible_bots:
                print(f"No bots found with rating >= {challenge_elo}")
                return False

            # Challenge random bot
            target_bot = random.choice(eligible_bots)
            self._lichess.create_challenge(
                username=target_bot,
                rated=True,
                clock_limit=challenge_time,
                clock_increment=challenge_increment,
                variant=settings.challenge_variant,
            )

            message = f"Challenged bot: {target_bot}"
            print(message)
            run_telegram_bot.send_message_to_telegram(self._telegram_token, message)

            self._retry_count = 0
            return True

        except Exception as e:
            print(f"Challenge error: {e}")
            self._retry_count += 1
            return False

    def create_user_challenge(self, username: str, time_sec: int, increment: int) -> None:
        """
        Create a challenge for a specific user (via Telegram).

        Args:
            username: Target username
            time_sec: Clock limit in seconds
            increment: Clock increment in seconds
        """
        try:
            self._lichess.create_challenge(
                username=username,
                rated=False,
                clock_limit=time_sec,
                clock_increment=increment,
            )
            message = f"Challenged user: {username}"
            print(message)
            run_telegram_bot.send_message_to_telegram(self._telegram_token, message)
            self._retry_count = 0
        except Exception as e:
            print(f"Failed to create challenge: {e}")

    def check_and_accept_challenges(self) -> None:
        """Check incoming challenges and accept/decline based on criteria."""
        try:
            challenges = self._lichess.get_my_challenges()

            for challenge in challenges.get("in", []):
                self._process_challenge(challenge)

        except Exception as e:
            print(f"Error checking challenges: {e}")

    def _process_challenge(self, challenge: dict) -> None:
        """Process a single challenge."""
        challenger = challenge["challenger"]["id"]
        challenge_id = challenge["id"]
        variant = challenge["variant"]["key"]

        try:
            speed = challenge.get("speed", challenge["timeControl"]["type"])
        except (KeyError, TypeError):
            speed = "unknown"

        try:
            if variant == "standard":
                self._handle_standard_challenge(challenge, challenger, challenge_id, speed)
            else:
                self._handle_variant_challenge(challenge, challenger, challenge_id, speed)

        except Exception as e:
            print(f"Error processing challenge from {challenger}: {e}")
            self._lichess.decline_challenge(challenge_id, "later")

    def _handle_standard_challenge(
        self, challenge: dict, challenger: str, challenge_id: str, speed: str
    ) -> None:
        """Handle standard chess challenges."""
        time_control = challenge.get("timeControl", {})

        # Accept correspondence games
        if speed == "correspondence" and time_control.get("type") != "unlimited":
            self._lichess.accept_challenge(challenge_id)
            print(f"Accepted correspondence challenge from {challenger}")
            return

        # Accept if time control meets requirements
        limit = time_control.get("limit", 0)
        increment = time_control.get("increment", 0)

        if (limit >= 900 and increment >= 14) or speed == "standard":
            self._lichess.accept_challenge(challenge_id)
            print(f"Accepted standard challenge from {challenger}")
        else:
            self._lichess.decline_challenge(challenge_id, "tooFast")
            print(f"Declined fast challenge from {challenger}")

    def _handle_variant_challenge(
        self, challenge: dict, challenger: str, challenge_id: str, speed: str
    ) -> None:
        """Handle variant chess challenges."""
        time_control = challenge.get("timeControl", {})
        limit = time_control.get("limit", 0)
        tc_type = time_control.get("type", "")

        if limit >= 120 and tc_type != "unlimited":
            self._lichess.accept_challenge(challenge_id)
            print(f"Accepted variant challenge from {challenger} on {speed}")
        else:
            self._lichess.decline_challenge(challenge_id, "generic")
            print(f"Declined variant challenge from {challenger}")


# =============================================================================
# FAST GAME HANDLER (THREADED)
# =============================================================================

class FastGameThread:
    """Handles fast games in a separate thread."""

    def __init__(
        self,
        game_id: str,
        variant: ChessVariant,
        game_handler: GameHandler,
        lichess: LichessClient,
        telegram_token: str,
    ) -> None:
        self._game_id = game_id
        self._variant = variant
        self._game_handler = game_handler
        self._lichess = lichess
        self._telegram_token = telegram_token
        self._counter = 0
        self._max_counter = 1000

    def run(self) -> int:
        """
        Run the fast game monitoring loop.

        Returns:
            10 when thread should exit
        """
        try:
            while True:
                self._counter += 1

                # Exit if counter exceeds max
                if self._counter >= self._max_counter:
                    return 10

                # Check ongoing games
                games = self._lichess.get_ongoing_games()

                for game in games:
                    if game["gameId"] != self._game_id:
                        continue

                    if not game["isMyTurn"]:
                        continue

                    # Reset counter while active
                    self._counter -= 1

                    # Send welcome message on first move
                    if not game.get("hasMoved", True):
                        self._game_handler._send_welcome_message(self._game_id)

                    # Handle the turn
                    self._game_handler.handle_turn(
                        game_id=self._game_id,
                        fen=game["fen"],
                        opponent_elo=game["opponent"]["rating"],
                        opponent_name=game["opponent"]["username"],
                        variant=self._variant,
                        is_fast_game=True,
                    )

                # Small sleep to prevent hammering the API
                time.sleep(0.5)

        except berserk.exceptions.ResponseError as e:
            print(f"Rate limit in fast game thread: {e}")
            run_telegram_bot.send_message_to_telegram(
                self._telegram_token, f"Rate limit in fast game {self._game_id}"
            )
            return 10

        except Exception as e:
            print(f"Error in fast game thread: {e}")
            run_telegram_bot.send_message_to_telegram(
                self._telegram_token, f"Error in fast game {self._game_id}: {e}"
            )
            return 10


# =============================================================================
# MAIN BOT CLASS
# =============================================================================

class ZoeChessBot:
    """
    Main chess bot class that orchestrates all components.

    This is the entry point for running the bot.

    Example:
        bot = ZoeChessBot()
        bot.run()
    """

    def __init__(self) -> None:
        self._paths = Paths()
        self._config = self._load_config()
        self._settings_db = SettingsDB(self._paths.settings_csv)
        self._chat_db = ChatDB(self._paths.chat_csv)
        self._lichess = LichessClient(self._config)
        self._engine = ChessEngine(self._paths, self._settings_db, self._config["tg_token"])
        self._game_handler = GameHandler(
            self._lichess,
            self._engine,
            self._chat_db,
            self._config["tg_token"],
        )
        self._challenge_manager = ChallengeManager(
            self._lichess,
            self._settings_db,
            self._config["tg_token"],
        )

        # Track active fast games
        self._active_fast_games: set[str] = set()
        self._challenge_counter = 0

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self._paths.config, "r") as f:
            return yaml.safe_load(f)

    def _should_check_challenges(self) -> bool:
        """Check if we should poll challenges this iteration."""
        return self._challenge_counter % 5 == 0

    def _should_send_challenge(self) -> bool:
        """Check if we should auto-send a challenge this iteration."""
        settings = self._settings_db.get_all_settings()
        threshold = max(100, settings.challenge_loops)
        return self._challenge_counter >= threshold

    def _start_fast_game_thread(self, game_id: str, variant: ChessVariant) -> None:
        """Start a thread for handling a fast game."""
        thread = FastGameThread(
            game_id,
            variant,
            self._game_handler,
            self._lichess,
            self._config["tg_token"],
        )

        t = threading.Thread(target=thread.run)
        t.daemon = True
        t.start()

        self._active_fast_games.add(game_id)
        print(f"Started fast game thread for {game_id}")

    def _is_fast_game(self, game: dict) -> bool:
        """Check if a game qualifies as fast (needs urgent attention)."""
        try:
            return game.get("secondsLeft", 999) <= FAST_GAME_THRESHOLD
        except (KeyError, TypeError):
            return False

    def _process_game(self, game: dict) -> None:
        """Process a single game state."""
        game_id = game["gameId"]
        variant = ChessVariant.from_string(game["variant"]["key"])

        # Skip if handled by fast game thread
        if game_id in self._active_fast_games:
            return

        # Check if it's our turn
        if not game["isMyTurn"]:
            return

        # Check if this is a fast game that needs a thread
        if self._is_fast_game(game) and game_id not in self._active_fast_games:
            self._start_fast_game_thread(game_id, variant)
            return

        # Send welcome message on first move
        if not game.get("hasMoved", True):
            self._game_handler._send_welcome_message(game_id)

        # Handle the turn
        self._game_handler.handle_turn(
            game_id=game_id,
            fen=game["fen"],
            opponent_elo=game["opponent"]["rating"],
            opponent_name=game["opponent"]["username"],
            variant=variant,
            is_fast_game=False,
        )

    def run(self) -> None:
        """
        Main bot loop. Runs indefinitely until interrupted.

        This is the entry point for the bot. It continuously:
        1. Polls for ongoing games
        2. Handles bot's turns
        3. Manages fast games via threads
        4. Sends/accepts challenges periodically
        """
        print("=" * 50)
        print("Zoe Chess Bot - Revisited 2026 Edition")
        print("=" * 50)
        print(f"Stockfish path: {self._paths.stockfish}")
        print(f"Fairy-Stockfish path: {self._paths.fairy_stockfish}")
        print("Bot is running... Press Ctrl+C to stop")
        print("=" * 50)

        try:
            while True:
                self._challenge_counter += 1

                # Check if we should auto-challenge
                if self._should_send_challenge():
                    self._challenge_counter = 0
                    self._challenge_manager.send_bot_challenge()

                # Check challenges periodically
                if self._should_check_challenges():
                    self._challenge_manager.check_and_accept_challenges()

                # Process ongoing games
                games = self._lichess.get_ongoing_games()
                for game in games:
                    self._process_game(game)

                # Small delay to prevent API hammering
                time.sleep(1)

        except berserk.exceptions.ResponseError as e:
            print(f"Rate limit exceeded: {e}")
            run_telegram_bot.send_message_to_telegram(
                self._config["tg_token"],
                f"Rate limit hit, restarting in {RATE_LIMIT_WAIT}s..."
            )
            time.sleep(RATE_LIMIT_WAIT)
            self.run()  # Restart

        except KeyboardInterrupt:
            print("\nBot stopped by user")

        except Exception as e:
            print(f"Unexpected error: {e}")
            run_telegram_bot.send_message_to_telegram(
                self._config["tg_token"],
                f"Bot error: {e}, restarting in {RATE_LIMIT_WAIT}s..."
            )
            time.sleep(RATE_LIMIT_WAIT)
            self.run()  # Restart


# =============================================================================
# PUBLIC API FOR TELEGRAM BOT
# =============================================================================

class BotAPI:
    """
    Public API for external integrations (e.g., Telegram bot).

    This provides a clean interface for the Telegram bot to interact
    with the chess bot without exposing internal details.
    """

    _instance: Optional[ZoeChessBot] = None

    @classmethod
    def initialize(cls) -> None:
        """Initialize the bot API (call once at startup)."""
        if cls._instance is None:
            paths = Paths()
            cls._instance = ZoeChessBot()

    @classmethod
    def create_challenge(cls, username: str, time_sec: int, increment: int) -> None:
        """Create a challenge for a specific user."""
        if cls._instance:
            cls._instance._challenge_manager.create_user_challenge(
                username, time_sec, increment
            )

    @classmethod
    def get_settings_db(cls) -> Optional[SettingsDB]:
        """Get the settings database for direct access."""
        if cls._instance:
            return cls._instance._settings_db
        return None


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    """
    Main entry point for the chess bot.

    Usage:
        python revisited2026.py

    Configuration:
        Edit config.yml with your Lichess and Telegram tokens.
        Ensure Stockfish binaries are in the correct paths.
    """
    bot = ZoeChessBot()
    bot.run()


if __name__ == "__main__":
    main()
