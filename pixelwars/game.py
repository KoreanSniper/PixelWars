from __future__ import annotations

import colorsys
import json
import math
import os
import random
import shutil
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pygame

from .online import DEFAULT_PORT, OnlineMatchClient, OnlineMatchServer, local_ip_hint


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
USER_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PixelWars" if getattr(sys, "frozen", False) else ROOT
MAP_DIR = BUNDLE_ROOT / "maps"
SAVE_DIR = USER_ROOT / "saves"
TERRITORY_IMAGE_DIR = USER_ROOT / "territory_images"
BUNDLED_TERRITORY_IMAGE_DIR = BUNDLE_ROOT / "territory_images"
GENERATED_MAP_DIR = USER_ROOT / "maps"
GAME_VERSION = "v1.0.5-alpha"
SCREEN_W = 1280
SCREEN_H = 820
PANEL_W = 300
MAP_VIEW_W = SCREEN_W - PANEL_W
DEFAULT_MAP_SIZE_KEY = "normal"
MAP_SIZE_OPTIONS = [
    ("small", "작음", 260),
    ("normal", "보통", 360),
    ("large", "큼", 460),
    ("huge", "초거대", 1018),
]
FPS = 60
ATTACKS_PER_FRAME = 10
PIXEL_ATTACK_COST = 0
NO_RESISTANCE_TROOPS = 10
ENEMY_TROOP_COST_RATIO = 0.006
ENEMY_DENSITY_COST_RATIO = 0.42
MAX_ATTACK_COST = 120
TROOPS_PER_PIXEL_CAP = 120
TEMP_OPERATION_GRACE = 60.0
SUPPLY_COLLAPSE_TIME = 180.0
SUPPLY_COLLAPSE_FLOOR = 0.25
SUPPLY_FACTORY_RANGE = 8
SUPPLY_RANGE = 36
LANDING_SPEED = 18
BALLISTIC_SPEED = 72
BALLISTIC_INTERCEPT_CHANCE = 0.65
BALLISTIC_COST = 360
NUKE_COST = 900
BALLISTIC_COOLDOWN = 45.0
NUKE_COOLDOWN = 90.0
NUKE_RADIUS = 30
FALLOUT_DURATION = 600.0
FALLOUT_TICK_INTERVAL = 1.0
BUILD_COOLDOWN = 5.0
AUTOSAVE_INTERVAL = 60.0
AUTOSAVE_KEEP = 5
VICTORY_CONTROL_RATIO = 0.95
VICTORY_HOLD_TIME = 120.0
ENEMY_SURVIVOR_PIXEL_LIMIT = 5
GAME_END_CHECK_INTERVAL = 1.0
PLAYER_ID = 0
DEFAULT_AI_COUNT = 20
AI_COUNT_OPTIONS = [20, 40, 60, 80, 100]
AI_COUNT_LABELS = {
    20: "소규모 전쟁",
    40: "표준 전쟁",
    60: "대규모 전쟁",
    80: "세계 대전",
    100: "혼돈",
}
NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))
TERRITORY_IMAGE_MODES = [
    ("tile", "타일"),
    ("stretch", "늘려 채우기"),
    ("cover", "잘라서 채우기"),
]
TERRAIN_LABELS = {"plain": "평원", "mountain": "산맥", "desert": "사막"}
TERRAIN_SPEED = {"plain": 1.0, "mountain": 0.8, "desert": 0.8}
BUILDING_HIDE_ZOOM = 3.0
WORLD_LOG_LIMIT = 8

PACE_OPTIONS = [
    {
        "key": "standard",
        "label": "표준",
        "description": "기본 실시간 전쟁",
        "attack_interval": 0.18,
        "ai_decision_interval": 0.5,
        "economy_interval_multiplier": 1.0,
        "ai_troop_multiplier": 1.0,
        "ai_money_multiplier": 1.0,
        "ai_chance_multiplier": 0.72,
    },
    {
        "key": "long",
        "label": "장기전",
        "description": "진격과 생산이 느려져 전선이 오래 유지됨",
        "attack_interval": 0.30,
        "ai_decision_interval": 0.8,
        "economy_interval_multiplier": 1.35,
        "ai_troop_multiplier": 1.02,
        "ai_money_multiplier": 1.02,
        "ai_chance_multiplier": 0.58,
    },
    {
        "key": "hard_ai",
        "label": "강한 AI",
        "description": "AI 자금과 병력, 행동성이 증가",
        "attack_interval": 0.22,
        "ai_decision_interval": 0.45,
        "economy_interval_multiplier": 1.05,
        "ai_troop_multiplier": 1.35,
        "ai_money_multiplier": 1.35,
        "ai_chance_multiplier": 1.28,
    },
]


BASE_COLORS = [
    (62, 156, 255),
    (230, 79, 79),
    (70, 190, 110),
    (229, 169, 65),
    (178, 105, 235),
    (229, 98, 160),
    (74, 208, 204),
    (180, 200, 76),
    (255, 122, 72),
    (108, 137, 245),
    (120, 214, 92),
    (245, 92, 112),
    (191, 143, 83),
    (74, 171, 155),
    (222, 115, 229),
    (138, 180, 78),
    (77, 118, 176),
    (218, 190, 91),
    (209, 85, 133),
    (112, 196, 226),
]


def faction_name(index: int) -> str:
    return "Player" if index == PLAYER_ID else f"AI {index:03d}"


def faction_color(index: int) -> tuple[int, int, int]:
    if index < len(BASE_COLORS):
        return BASE_COLORS[index]
    hue = (index * 137) % 360
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 0.68, 0.92)
    return int(r * 255), int(g * 255), int(b * 255)


AI_PERSONALITIES = {
    "balanced": {
        "label": "균형",
        "operation_chance": 0.010,
        "operation_troops": 180,
        "max_operations": 2,
        "air_chance": 0.004,
        "ballistic_chance": 0.00018,
        "build_chance": 0.014,
        "build_choices": ["city", "sam", "airbase", "factory", "supply"],
    },
    "aggressive": {
        "label": "공격적",
        "operation_chance": 0.026,
        "operation_troops": 280,
        "max_operations": 3,
        "air_chance": 0.008,
        "ballistic_chance": 0.00035,
        "build_chance": 0.010,
        "build_choices": ["airbase", "factory", "city", "supply"],
    },
    "defensive": {
        "label": "방어",
        "operation_chance": 0.006,
        "operation_troops": 120,
        "max_operations": 1,
        "air_chance": 0.002,
        "ballistic_chance": 0.00015,
        "build_chance": 0.020,
        "build_choices": ["sam", "factory", "city", "sam", "supply"],
    },
    "economic": {
        "label": "경제",
        "operation_chance": 0.01,
        "operation_troops": 150,
        "max_operations": 2,
        "air_chance": 0.0025,
        "ballistic_chance": 0.00018,
        "build_chance": 0.022,
        "build_choices": ["city", "factory", "port", "city", "supply"],
    },
    "raider": {
        "label": "약탈",
        "operation_chance": 0.022,
        "operation_troops": 170,
        "max_operations": 3,
        "air_chance": 0.012,
        "ballistic_chance": 0.00045,
        "build_chance": 0.011,
        "build_choices": ["airbase", "factory", "sam", "supply"],
    },
    "berserker": {
        "label": "극공",
        "operation_chance": 0.052,
        "operation_troops": 430,
        "max_operations": 4,
        "air_chance": 0.018,
        "ballistic_chance": 0.00055,
        "build_chance": 0.008,
        "build_choices": ["airbase", "factory", "supply"],
    },
    "turtle": {
        "label": "극방",
        "operation_chance": 0.002,
        "operation_troops": 80,
        "max_operations": 1,
        "air_chance": 0.001,
        "ballistic_chance": 0.00005,
        "build_chance": 0.026,
        "build_choices": ["sam", "sam", "factory", "city", "supply"],
    },
}


def ai_personality(index: int) -> str:
    if index == PLAYER_ID:
        return "player"
    if index % 25 == 0:
        return "berserker"
    if index % 20 == 0:
        return "turtle"
    cycle = ["balanced", "aggressive", "defensive", "economic", "raider"]
    return cycle[index % len(cycle)]


@dataclass
class Faction:
    name: str
    color: tuple[int, int, int]
    money: int = 420
    troops: int = 1000
    fighters: int = 0
    bombers: int = 0
    ships: int = 0
    alive: bool = True
    ai_timer: float = 0.0
    personality: str = "balanced"
    unsupplied_time: float = 0.0
    unsupplied_start_troops: int | None = None
    ballistic_cooldown: float = 0.0
    nuke_cooldown: float = 0.0


@dataclass
class Building:
    kind: str
    owner: int
    x: int
    y: int
    level: int = 1
    timer: float = 0.0


@dataclass
class Unit:
    kind: str
    owner: int
    x: float
    y: float
    tx: float
    ty: float
    source: tuple[int, int] | None = None
    target_cell: tuple[int, int] | None = None
    returning: bool = False
    payload: int = 0
    speed: float = 42.0
    operation_target: int | None = None
    path: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Operation:
    owner: int
    target: int | None
    troops: int
    pixel_cost: int = PIXEL_ATTACK_COST
    label: str = "작전"
    cells: set[tuple[int, int]] | None = None
    focus: tuple[int, int] | None = None
    timer: float = 0.0
    age: float = 0.0
    supply_grace: float = 0.0
    finished: bool = False


@dataclass
class Menu:
    x: int
    y: int
    map_x: int
    map_y: int
    options: list[tuple[str, str]]
    title: str = "작전"


class PixelWars:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("PixelWars")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic", 18)
        self.small = pygame.font.SysFont("malgungothic", 14)
        self.big = pygame.font.SysFont("malgungothic", 26, bold=True)

        self.map_size_key = DEFAULT_MAP_SIZE_KEY
        self.ai_count = DEFAULT_AI_COUNT
        self.pace_key = "standard"
        self.map_files = self.discover_maps()
        self.map_index = 0
        self.raw_map: pygame.Surface
        self.map_surface: pygame.Surface
        self.owner_overlay: pygame.Surface
        self.territory_image_overlay: pygame.Surface
        self.terrain_overlay: pygame.Surface
        self.map_view_rect = pygame.Rect(0, 0, MAP_VIEW_W, SCREEN_H)
        self.base_scale = 1.0
        self.scale = 1.0
        self.camera_x = 12.0
        self.camera_y = 12.0
        self.width = 1
        self.height = 1
        self.land: list[list[bool]] = []
        self.terrain: list[list[str]] = []
        self.prepared_terrain: list[list[str]] = []
        self.owner: list[list[int | None]] = []
        self.frontiers: list[set[tuple[int, int]]] = []
        self.territory_counts: list[int] = []
        self.factions: list[Faction] = []
        self.buildings: list[Building] = []
        self.units: list[Unit] = []
        self.operations: list[Operation] = []
        self.wars: set[frozenset[int]] = set()
        self.active_supply_sources: dict[int, list[tuple[int, int]]] = {}
        self.active_supply_ranges: dict[int, dict[tuple[int, int], int]] = {}
        self.active_supply_links: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
        self.fallout: dict[tuple[int, int], float] = {}
        self.fallout_timer = 0.0
        self.build_cooldowns: dict[int, float] = {}
        self.supply_dirty = True
        self.menu: Menu | None = None
        self.operation_cancel_rects: list[tuple[pygame.Rect, Operation]] = []
        self.selected_target: int | None = None
        self.show_buildings = True
        self.show_support_zones = "off"
        self.show_owner_borders = False
        self.show_ai_traits = False
        self.show_operation_info = False
        self.territory_images_enabled = True
        self.territory_image_file: str | None = None
        self.territory_image_mode = "tile"
        self.territory_images: dict[int, pygame.Surface] = {}
        self.territory_image_files: list[Path] = []
        self.outline_boundary_cells: set[tuple[int, int]] = set()
        self.last_supply_buildings_hash = 0
        self.pause_buttons: list[tuple[str, pygame.Rect]] = []
        self.pause_menu_page = "main"
        self.world_log: list[str] = []
        self.operation_percent = 0.25
        self.status = "좌클릭으로 작전 생성, 우클릭으로 작전 메뉴"
        self.slider_drag = False
        self.sidebar_collapsed = False
        self.panel_scroll = 0
        self.panel_content_height = SCREEN_H
        self.choosing_capital = True
        self.game_over = False
        self.game_result: str | None = None
        self.victory_timer = 0.0
        self.game_end_check_timer = 0.0
        self.paused = False
        self.sim_speed = 1.0
        self.screen_mode = "lobby"
        self.match_timer = 0.0
        self.match_duration = 3.0
        self.match_found = 0
        self.lobby_buttons: list[tuple[str, pygame.Rect]] = []
        self.minimap_rect = pygame.Rect(0, 0, 0, 0)
        self.online_server: OnlineMatchServer | None = None
        self.online_client: OnlineMatchClient | None = None
        self.online_status = "온라인: 연결 안 됨"
        self.online_host_hint = local_ip_hint()
        self.join_host_text = "127.0.0.1"
        self.join_host_active = False
        self.online_ready = False
        self.show_help = False
        self.show_save_picker = False
        self.save_picker_scroll = 0
        self.save_picker_items: list[Path] = []
        self.save_picker_meta: dict[Path, str] = {}
        self.ai_decision_timer = 0.0
        self.autosave_timer = 0.0
        self.running = True
        self.load_random_map()
        self.status = "로비: 매칭 시작을 누르세요"

    def load_map(self, index: int) -> None:
        self.map_files = self.discover_maps()
        self.map_index = index % len(self.map_files)
        loaded_map = pygame.image.load(str(self.map_files[self.map_index])).convert_alpha()
        self.raw_map = self.prepare_map_surface(loaded_map)
        max_w = MAP_VIEW_W - 24
        max_h = SCREEN_H - 24
        self.base_scale = max(0.25, min(max_w / self.raw_map.get_width(), max_h / self.raw_map.get_height()))
        self.scale = self.base_scale
        self.width = self.raw_map.get_width()
        self.height = self.raw_map.get_height()
        self.camera_x = 12
        self.camera_y = 12
        self.rebuild_map_surface()
        self.land = [[False for _ in range(self.height)] for _ in range(self.width)]
        self.terrain = [column[:] for column in self.prepared_terrain] if self.prepared_terrain else [["plain" for _ in range(self.height)] for _ in range(self.width)]
        for x in range(self.width):
            for y in range(self.height):
                r, g, b, a = self.raw_map.get_at((x, y))
                self.land[x][y] = self.is_land_color(r, g, b, a)
                if not self.land[x][y]:
                    self.terrain[x][y] = "water"
        if sum(1 for x in range(self.width) for y in range(self.height) if self.land[x][y]) < self.width * self.height * 0.08:
            self.land = [[True for _ in range(self.height)] for _ in range(self.width)]
            self.terrain = [["plain" for _ in range(self.height)] for _ in range(self.width)]
        else:
            self.repair_thin_land_gaps()
            self.rebuild_map_surface()
        self.owner = [[None for _ in range(self.height)] for _ in range(self.width)]
        self.owner_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.territory_image_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.terrain_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.rebuild_terrain_overlay()
        self.load_territory_images()
        self.factions = [
            Faction(faction_name(i), faction_color(i), personality=ai_personality(i))
            for i in range(self.ai_count + 1)
        ]
        self.apply_pace_starting_resources()
        self.frontiers = [set() for _ in self.factions]
        self.territory_counts = [0 for _ in self.factions]
        self.buildings = []
        self.units = []
        self.operations = []
        self.wars = set()
        self.active_supply_sources = {}
        self.active_supply_ranges = {}
        self.active_supply_links = {}
        self.fallout = {}
        self.fallout_timer = 0.0
        self.build_cooldowns = {}
        self.supply_dirty = True
        self.menu = None
        self.operation_cancel_rects = []
        self.selected_target = None
        self.choosing_capital = True
        self.game_over = False
        self.game_result = None
        self.victory_timer = 0.0
        self.game_end_check_timer = 0.0
        self.paused = False
        self.sim_speed = 1.0
        self.ai_decision_timer = 0.0
        self.autosave_timer = 0.0
        self.world_log = []
        self.seed_factions()
        self.rebuild_territory_counts()
        self.rebuild_owner_overlay()
        self.rebuild_frontiers()
        self.rebuild_supply_networks()
        self.status = "수도를 세울 육지를 좌클릭하세요"

    def load_territory_images(self) -> None:
        self.territory_images = {}
        TERRITORY_IMAGE_DIR.mkdir(exist_ok=True)
        image_dirs = [TERRITORY_IMAGE_DIR]
        if BUNDLED_TERRITORY_IMAGE_DIR != TERRITORY_IMAGE_DIR and BUNDLED_TERRITORY_IMAGE_DIR.exists():
            image_dirs.append(BUNDLED_TERRITORY_IMAGE_DIR)
        by_name: dict[str, Path] = {}
        for image_dir in reversed(image_dirs):
            if image_dir.exists():
                for path in image_dir.iterdir():
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}:
                        by_name[path.name] = path
        self.territory_image_files = sorted(by_name.values(), key=lambda path: path.name.lower())
        selected_path = by_name.get(self.territory_image_file or "")
        if self.territory_image_file and selected_path is None:
            self.territory_image_file = None
        if self.territory_image_file is None:
            selected_path = next((by_name[name] for name in ("player.png", "0.png", "faction_0.png") if name in by_name), self.territory_image_files[0] if self.territory_image_files else None)
            self.territory_image_file = selected_path.name if selected_path else None
        else:
            selected_path = by_name.get(self.territory_image_file)
        if selected_path:
            try:
                self.territory_images[PLAYER_ID] = pygame.image.load(str(selected_path)).convert_alpha()
            except pygame.error:
                self.territory_image_file = None

    def territory_image_mode_label(self) -> str:
        return next((label for key, label in TERRITORY_IMAGE_MODES if key == self.territory_image_mode), "타일")

    def support_zones_label(self) -> str:
        labels = {"off": "끔", "outline": "테두리만", "full": "전체"}
        return labels.get(self.show_support_zones, "끔")

    def ai_count_label(self) -> str:
        return AI_COUNT_LABELS.get(self.ai_count, f"AI {self.ai_count}")

    def building_visible_at_current_zoom(self) -> bool:
        return self.show_buildings and self.scale / max(0.001, self.base_scale) < BUILDING_HIDE_ZOOM

    def add_world_log(self, message: str) -> None:
        self.world_log.insert(0, message)
        del self.world_log[WORLD_LOG_LIMIT:]

    def load_random_map(self) -> None:
        self.map_files = self.discover_maps()
        self.load_map(random.randrange(len(self.map_files)))

    def discover_maps(self) -> list[Path]:
        map_dirs = [MAP_DIR]
        if GENERATED_MAP_DIR != MAP_DIR:
            map_dirs.append(GENERATED_MAP_DIR)
        maps: list[Path] = []
        seen: set[str] = set()
        for map_dir in map_dirs:
            if not map_dir.exists():
                continue
            for path in sorted(map_dir.glob("*.png")):
                if path.name not in seen:
                    maps.append(path)
                    seen.add(path.name)
        if not maps:
            maps = [self.create_fallback_map()]
        return maps

    def create_fallback_map(self) -> Path:
        GENERATED_MAP_DIR.mkdir(parents=True, exist_ok=True)
        path = GENERATED_MAP_DIR / "fallback_world.png"
        if path.exists():
            return path
        surface = pygame.Surface((420, 260), pygame.SRCALPHA)
        surface.fill((135, 206, 235, 255))
        land_color = (255, 255, 255, 255)
        for rect in [
            pygame.Rect(34, 54, 128, 74),
            pygame.Rect(78, 126, 96, 88),
            pygame.Rect(198, 46, 148, 92),
            pygame.Rect(244, 136, 110, 68),
        ]:
            pygame.draw.ellipse(surface, land_color, rect)
        pygame.draw.circle(surface, land_color, (370, 190), 24)
        pygame.image.save(surface, path)
        self.status = "맵 폴더가 비어 있어 기본 fallback 맵을 생성했습니다"
        return path

    def prepare_map_surface(self, source: pygame.Surface) -> pygame.Surface:
        width, height = source.get_size()
        scale = self.current_map_max_dim() / max(width, height)
        if abs(scale - 1.0) > 0.03:
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))
            source = pygame.transform.smoothscale(source, (width, height))
        prepared = pygame.Surface((width, height), pygame.SRCALPHA)
        self.prepared_terrain = [["plain" for _ in range(height)] for _ in range(width)]
        for x in range(width):
            for y in range(height):
                r, g, b, a = source.get_at((x, y))
                land = self.is_land_color(r, g, b, a)
                self.prepared_terrain[x][y] = self.classify_terrain(r, g, b, a) if land else "water"
                prepared.set_at((x, y), (255, 255, 255, 255) if land else (135, 206, 235, 255))
        return prepared

    def classify_terrain(self, r: int, g: int, b: int, a: int) -> str:
        if a < 24:
            return "water"
        if r >= 220 and g >= 220 and b >= 220:
            return "plain"
        if abs(r - g) <= 28 and abs(g - b) <= 28 and 85 <= r <= 190:
            return "mountain"
        if r >= 185 and g >= 145 and b <= 115:
            return "desert"
        return "plain"

    def current_map_max_dim(self) -> int:
        for key, _label, max_dim in MAP_SIZE_OPTIONS:
            if key == self.map_size_key:
                return max_dim
        return 360

    def map_size_label(self) -> str:
        for key, label, _max_dim in MAP_SIZE_OPTIONS:
            if key == self.map_size_key:
                return label
        return "보통"

    def pace_option(self) -> dict[str, float | str]:
        for option in PACE_OPTIONS:
            if option["key"] == self.pace_key:
                return option
        return PACE_OPTIONS[0]

    def pace_label(self) -> str:
        return str(self.pace_option()["label"])

    def pace_description(self) -> str:
        return str(self.pace_option()["description"])

    def apply_pace_starting_resources(self) -> None:
        option = self.pace_option()
        troop_multiplier = float(option["ai_troop_multiplier"])
        money_multiplier = float(option["ai_money_multiplier"])
        for fid, faction in enumerate(self.factions):
            if fid == PLAYER_ID:
                continue
            faction.troops = int(faction.troops * troop_multiplier)
            faction.money = int(faction.money * money_multiplier)

    def is_land_color(self, r: int, g: int, b: int, a: int) -> bool:
        if a < 24:
            return False
        # The current maps use strong contrast: white land, sky-blue water.
        if r >= 220 and g >= 220 and b >= 220:
            return True
        if b >= 150 and g >= 120 and r <= 190 and b >= r + 35:
            return False
        brightness = (r + g + b) / 3
        saturation = max(r, g, b) - min(r, g, b)
        if brightness >= 205 and saturation <= 45:
            return True
        return not (b > 105 and b > r + 16 and b > g + 8)

    def repair_thin_land_gaps(self) -> None:
        repaired: list[tuple[int, int]] = []
        for x in range(1, self.width - 1):
            for y in range(1, self.height - 1):
                if self.land[x][y]:
                    continue
                horizontal_bridge = self.land[x - 1][y] and self.land[x + 1][y]
                vertical_bridge = self.land[x][y - 1] and self.land[x][y + 1]
                diagonal_support = sum(
                    1
                    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1))
                    if self.land[x + dx][y + dy]
                )
                if horizontal_bridge or vertical_bridge or diagonal_support >= 3:
                    repaired.append((x, y))
        for x, y in repaired:
            self.land[x][y] = True
            self.terrain[x][y] = "plain"
            self.raw_map.set_at((x, y), (255, 255, 255, 255))

    def rebuild_map_surface(self) -> None:
        scaled_w = max(1, int(self.width * self.scale))
        scaled_h = max(1, int(self.height * self.scale))
        self.map_surface = pygame.transform.smoothscale(self.raw_map, (scaled_w, scaled_h))
        self.clamp_camera()

    def rebuild_terrain_overlay(self) -> None:
        self.terrain_overlay.fill((0, 0, 0, 0))
        colors = {"mountain": (105, 112, 118, 70), "desert": (224, 176, 82, 58)}
        for x in range(self.width):
            for y in range(self.height):
                color = colors.get(self.terrain[x][y])
                if color:
                    self.terrain_overlay.set_at((x, y), color)

    def seed_factions(self) -> None:
        land_cells = [(x, y) for x in range(self.width) for y in range(self.height) if self.land[x][y]]
        random.shuffle(land_cells)
        seeds: list[tuple[int, int]] = []
        min_dist = max(3, int(math.sqrt(self.width * self.height / (max(1, len(self.factions)) * 1.8))))
        target_seed_count = max(0, len(self.factions) - 1)
        for cell in land_cells:
            if len(seeds) >= target_seed_count:
                break
            if all(abs(cell[0] - sx) + abs(cell[1] - sy) >= min_dist for sx, sy in seeds):
                seeds.append(cell)
            if len(seeds) >= target_seed_count:
                break
        if len(seeds) < target_seed_count:
            seeds = land_cells[:target_seed_count]
        for fid, (sx, sy) in enumerate(seeds, start=1):
            for x in range(max(0, sx - 2), min(self.width, sx + 3)):
                for y in range(max(0, sy - 2), min(self.height, sy + 3)):
                    if self.land[x][y] and abs(x - sx) + abs(y - sy) <= 3:
                        self.owner[x][y] = fid
            self.buildings.append(Building("city", fid, sx, sy))
            self.buildings.append(Building("factory", fid, sx, sy))

    def place_player_capital(self, sx: int, sy: int) -> None:
        if not self.land[sx][sy]:
            self.status = "수도는 육지에만 세울 수 있습니다"
            return
        for x in range(max(0, sx - 3), min(self.width, sx + 4)):
            for y in range(max(0, sy - 3), min(self.height, sy + 4)):
                if self.land[x][y] and abs(x - sx) + abs(y - sy) <= 4:
                    self.set_owner(x, y, PLAYER_ID)
                    self.destroy_buildings_at(x, y)
        self.buildings.append(Building("city", PLAYER_ID, sx, sy))
        self.buildings.append(Building("factory", PLAYER_ID, sx, sy))
        self.ensure_minimum_start_land(PLAYER_ID, sx, sy, self.factions[PLAYER_ID].troops)
        self.mark_supply_dirty()
        self.factions[PLAYER_ID].alive = True
        self.choosing_capital = False
        self.status = "수도 건설 완료: 도시와 공장 가동"

    def auto_place_capital(self) -> None:
        candidates = self.best_capital_region()
        if not candidates:
            self.status = "자동 수도 실패: 육지가 없음"
            return
        center_x, center_y = self.width / 2, self.height / 2
        x, y = min(candidates, key=lambda cell: (cell[0] - center_x) ** 2 + (cell[1] - center_y) ** 2)
        self.place_player_capital(x, y)
        self.status = "자동 수도 배치 완료"

    def best_capital_region(self) -> list[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        best: list[tuple[int, int]] = []
        for sx in range(self.width):
            for sy in range(self.height):
                start = (sx, sy)
                if start in visited or not self.land[sx][sy] or self.owner[sx][sy] is not None:
                    continue
                component: list[tuple[int, int]] = []
                queue = deque([start])
                visited.add(start)
                while queue:
                    x, y = queue.popleft()
                    component.append((x, y))
                    for dx, dy in NEIGHBORS:
                        nx, ny = x + dx, y + dy
                        nxt = (nx, ny)
                        if (
                            0 <= nx < self.width
                            and 0 <= ny < self.height
                            and nxt not in visited
                            and self.land[nx][ny]
                            and self.owner[nx][ny] is None
                        ):
                            visited.add(nxt)
                            queue.append(nxt)
                if len(component) > len(best):
                    best = component
        if best:
            return best
        return [(x, y) for x in range(self.width) for y in range(self.height) if self.land[x][y]]

    def ensure_minimum_start_land(self, owner: int, sx: int, sy: int, troops: int) -> None:
        queue = deque([(sx, sy)])
        visited = {(sx, sy)}
        while queue and self.troop_capacity(owner) < troops:
            x, y = queue.popleft()
            if 0 <= x < self.width and 0 <= y < self.height and self.land[x][y]:
                self.set_owner(x, y, owner)
            for dx, dy in NEIGHBORS:
                nxt = (x + dx, y + dy)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

    def set_owner(self, x: int, y: int, owner: int | None) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        old_owner = self.owner[x][y]
        if old_owner == owner:
            return
        if old_owner is not None:
            self.territory_counts[old_owner] = max(0, self.territory_counts[old_owner] - 1)
            self.clamp_faction_troops(old_owner)
        if owner is not None:
            self.territory_counts[owner] += 1
        self.owner[x][y] = owner
        self.update_owner_overlay_cell(x, y)
        self.refresh_frontier_neighborhood(x, y)

    def rebuild_territory_counts(self) -> None:
        self.territory_counts = [0 for _ in self.factions]
        for x in range(self.width):
            for y in range(self.height):
                owner = self.owner[x][y]
                if owner is not None:
                    self.territory_counts[owner] += 1

    def rebuild_owner_overlay(self) -> None:
        self.owner_overlay.fill((0, 0, 0, 0))
        self.territory_image_overlay.fill((0, 0, 0, 0))
        for x in range(self.width):
            for y in range(self.height):
                self.update_owner_overlay_cell(x, y)

    def update_owner_overlay_cell(self, x: int, y: int) -> None:
        owner = self.owner[x][y]
        if owner is None:
            self.owner_overlay.set_at((x, y), (0, 0, 0, 0))
            self.territory_image_overlay.set_at((x, y), (0, 0, 0, 0))
        else:
            self.owner_overlay.set_at((x, y), (*self.factions[owner].color, 112))
            texture = self.territory_images.get(owner)
            if texture:
                r, g, b, a = self.sample_territory_image(texture, x, y)
                self.territory_image_overlay.set_at((x, y), (r, g, b, min(180, a)))
            else:
                self.territory_image_overlay.set_at((x, y), (0, 0, 0, 0))

    def sample_territory_image(self, texture: pygame.Surface, x: int, y: int) -> tuple[int, int, int, int]:
        tw, th = texture.get_size()
        if tw <= 0 or th <= 0:
            return 0, 0, 0, 0
        if self.territory_image_mode == "stretch":
            tx = min(tw - 1, max(0, int(x / max(1, self.width - 1) * (tw - 1))))
            ty = min(th - 1, max(0, int(y / max(1, self.height - 1) * (th - 1))))
        elif self.territory_image_mode == "cover":
            scale = max(self.width / tw, self.height / th)
            draw_w, draw_h = tw * scale, th * scale
            offset_x = (self.width - draw_w) / 2
            offset_y = (self.height - draw_h) / 2
            tx = min(tw - 1, max(0, int((x - offset_x) / scale)))
            ty = min(th - 1, max(0, int((y - offset_y) / scale)))
        else:
            tx, ty = x % tw, y % th
        return texture.get_at((tx, ty))

    def rebuild_frontiers(self) -> None:
        self.frontiers = [set() for _ in self.factions]
        for x in range(self.width):
            for y in range(self.height):
                self.refresh_frontier_cell(x, y)

    def refresh_frontier_neighborhood(self, x: int, y: int) -> None:
        for cx, cy in [(x, y), *[(x + dx, y + dy) for dx, dy in NEIGHBORS]]:
            self.refresh_frontier_cell(cx, cy)

    def refresh_frontier_cell(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        cell = (x, y)
        for frontier in self.frontiers:
            frontier.discard(cell)
        if not self.land[x][y]:
            return
        current = self.owner[x][y]
        neighbor_owners = {
            self.owner[x + dx][y + dy]
            for dx, dy in NEIGHBORS
            if 0 <= x + dx < self.width and 0 <= y + dy < self.height
        }
        for fid in neighbor_owners:
            if fid is not None and fid != current:
                self.frontiers[fid].add(cell)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            self.update_layout()
            self.handle_events()
            self.update(dt)
            self.draw()
        self.shutdown_online()
        pygame.quit()

    def sidebar_width(self) -> int:
        return 46 if self.sidebar_collapsed else PANEL_W

    def panel_rect(self) -> pygame.Rect:
        width = self.sidebar_width()
        return pygame.Rect(SCREEN_W - width, 0, width, SCREEN_H)

    def update_layout(self) -> None:
        self.map_view_rect = pygame.Rect(0, 0, SCREEN_W - self.sidebar_width(), SCREEN_H)
        self.clamp_camera()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.show_save_picker and event.key == pygame.K_ESCAPE:
                    self.show_save_picker = False
                    continue
                if self.screen_mode == "lobby":
                    if self.join_host_active:
                        self.handle_join_host_key(event)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_matchmaking()
                    elif event.key == pygame.K_1:
                        self.load_map(self.map_index - 1)
                        self.screen_mode = "lobby"
                        self.status = "로비: 이전 맵 선택"
                    elif event.key == pygame.K_2:
                        self.load_map(self.map_index + 1)
                        self.screen_mode = "lobby"
                        self.status = "로비: 다음 맵 선택"
                    elif event.key == pygame.K_r:
                        self.load_random_map()
                        self.screen_mode = "lobby"
                        self.status = "로비: 랜덤 맵 선택"
                    elif event.key == pygame.K_3:
                        self.cycle_map_size()
                    elif event.key == pygame.K_4:
                        self.cycle_ai_count()
                    elif event.key == pygame.K_5:
                        self.cycle_pace()
                    elif event.key in (pygame.K_h, pygame.K_F1, pygame.K_SLASH):
                        self.show_help = not self.show_help
                    continue
                if self.screen_mode == "matching":
                    if event.key == pygame.K_ESCAPE:
                        self.screen_mode = "lobby"
                        self.status = "매칭 취소"
                    continue
                if event.key == pygame.K_ESCAPE:
                    if self.show_save_picker:
                        self.show_save_picker = False
                    elif self.show_help:
                        self.show_help = False
                    elif self.paused:
                        self.toggle_pause()
                    elif self.menu:
                        self.menu = None
                        self.status = "메뉴 닫힘"
                    else:
                        self.toggle_pause()
                elif event.key == pygame.K_1:
                    self.load_map(self.map_index - 1)
                elif event.key == pygame.K_2:
                    self.load_map(self.map_index + 1)
                elif event.key == pygame.K_r:
                    self.load_random_map()
                elif event.key in (pygame.K_h, pygame.K_F1, pygame.K_SLASH):
                    self.show_help = not self.show_help
                elif event.key == pygame.K_g:
                    self.toggle_building_display()
                elif event.key == pygame.K_t:
                    self.toggle_territory_images()
                elif event.key == pygame.K_l:
                    self.return_to_lobby()
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self.change_sim_speed(1)
                elif event.key == pygame.K_MINUS:
                    self.change_sim_speed(-1)
                elif event.key == pygame.K_c:
                    if self.choosing_capital:
                        self.auto_place_capital()
                    else:
                        self.toggle_ai_traits()
                elif event.key == pygame.K_v:
                    self.toggle_support_zones()
                elif event.key == pygame.K_e:
                    self.toggle_operation_info()
                elif event.key == pygame.K_TAB:
                    self.sidebar_collapsed = not self.sidebar_collapsed
                    self.update_layout()
                elif event.key == pygame.K_F5:
                    self.save_game()
                elif event.key == pygame.K_F9:
                    self.open_save_picker()
                elif event.key == pygame.K_f:
                    self.buy_aircraft("fighter")
                elif event.key == pygame.K_b:
                    self.buy_aircraft("bomber")
                elif event.key == pygame.K_n:
                    self.buy_ship()
            elif event.type == pygame.MOUSEWHEEL:
                mouse = pygame.mouse.get_pos()
                if self.show_save_picker:
                    self.scroll_save_picker(event.y)
                elif self.panel_rect().collidepoint(mouse) and not self.sidebar_collapsed:
                    self.scroll_panel(event.y)
                elif self.map_view_rect.collidepoint(mouse):
                    self.zoom_at(mouse[0], mouse[1], 1.16 if event.y > 0 else 1 / 1.16)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.on_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.slider_drag = False
            elif event.type == pygame.MOUSEMOTION and self.slider_drag:
                self.update_slider(event.pos[0])

    def on_mouse_down(self, event: pygame.event.Event) -> None:
        mx, my = event.pos
        if self.show_save_picker:
            self.click_save_picker(mx, my)
            return
        if self.show_help:
            self.show_help = False
            return
        if self.paused and event.button == 1 and self.click_pause_menu(mx, my):
            return
        if self.screen_mode == "lobby":
            self.join_host_active = False
            self.click_lobby(mx, my)
            return
        if self.screen_mode == "matching":
            return
        if self.game_over:
            return
        if self.menu and event.button == 1 and self.click_menu(mx, my):
            return
        if not self.sidebar_collapsed and event.button == 1 and self.click_operation_cancel(mx, my):
            return
        if not self.sidebar_collapsed and event.button == 1 and self.click_minimap(mx, my):
            return
        if not self.sidebar_collapsed and event.button == 1 and self.slider_rect().collidepoint(mx, my):
            self.slider_drag = True
            self.update_slider(mx)
            return
        cell = self.screen_to_cell(mx, my)
        if event.button == 1 and cell:
            x, y = cell
            if self.choosing_capital:
                self.place_player_capital(x, y)
                self.menu = None
                return
            self.selected_target = self.owner[x][y]
            self.create_operation(PLAYER_ID, self.selected_target, self.selected_operation_troops(), "좌클릭 작전", focus=(x, y))
            self.menu = None
        elif event.button == 3 and cell and not self.choosing_capital:
            x, y = cell
            self.open_context_menu(mx, my, x, y)

    def click_minimap(self, mx: int, my: int) -> bool:
        if not self.minimap_rect.collidepoint(mx, my) or self.minimap_rect.w <= 0 or self.minimap_rect.h <= 0:
            return False
        local_x = (mx - self.minimap_rect.x) / self.minimap_rect.w
        local_y = (my - self.minimap_rect.y) / self.minimap_rect.h
        target_x = local_x * self.width
        target_y = local_y * self.height
        self.camera_x = self.map_view_rect.w / 2 - target_x * self.scale
        self.camera_y = self.map_view_rect.h / 2 - target_y * self.scale
        self.clamp_camera()
        return True

    def click_operation_cancel(self, mx: int, my: int) -> bool:
        for rect, operation in self.operation_cancel_rects:
            if rect.collidepoint(mx, my):
                if operation in self.operations:
                    self.operations.remove(operation)
                    self.refund_operation_troops(operation)
                    self.status = f"{operation.label} 취소"
                return True
        return False

    def click_pause_menu(self, mx: int, my: int) -> bool:
        for action, rect in self.pause_buttons:
            if not rect.collidepoint(mx, my):
                continue
            if action == "resume":
                self.toggle_pause()
            elif action == "save":
                self.save_game()
            elif action == "load":
                self.open_save_picker()
            elif action == "buildings":
                self.toggle_building_display()
            elif action == "support_zones":
                self.toggle_support_zones()
            elif action == "borders":
                self.toggle_owner_borders()
            elif action == "territory_images":
                self.toggle_territory_images()
            elif action == "settings":
                self.pause_menu_page = "settings"
            elif action == "back":
                self.pause_menu_page = "main"
            elif action == "image_prev":
                self.cycle_territory_image(-1)
            elif action == "image_next":
                self.cycle_territory_image(1)
            elif action == "image_mode":
                self.cycle_territory_image_mode()
            elif action == "image_upload":
                self.upload_territory_image()
            elif action == "lobby":
                self.return_to_lobby()
            elif action == "quit":
                self.running = False
            return True
        return False

    def click_lobby(self, mx: int, my: int) -> None:
        for action, rect in self.lobby_buttons:
            if not rect.collidepoint(mx, my):
                continue
            if action == "match":
                self.start_matchmaking()
            elif action == "prev_map":
                self.load_map(self.map_index - 1)
                self.screen_mode = "lobby"
                self.status = "로비: 이전 맵 선택"
            elif action == "next_map":
                self.load_map(self.map_index + 1)
                self.screen_mode = "lobby"
                self.status = "로비: 다음 맵 선택"
            elif action == "random_map":
                self.load_random_map()
                self.screen_mode = "lobby"
                self.status = "로비: 랜덤 맵 선택"
            elif action == "map_size":
                self.cycle_map_size()
            elif action == "ai_count":
                self.cycle_ai_count()
            elif action == "pace":
                self.cycle_pace()
            elif action == "load_save":
                self.open_save_picker()
            elif action == "host_online":
                self.host_online_lobby()
            elif action == "join_local":
                self.join_online_lobby("127.0.0.1")
            elif action == "join_host":
                self.join_online_lobby(self.join_host_text.strip() or "127.0.0.1")
            elif action == "host_input":
                self.join_host_active = True
            elif action == "toggle_ready":
                self.toggle_online_ready()
            elif action == "disconnect_online":
                self.disconnect_online()
            return

    def handle_join_host_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.join_host_active = False
            return
        if event.key == pygame.K_RETURN:
            self.join_host_active = False
            self.join_online_lobby(self.join_host_text.strip() or "127.0.0.1")
            return
        if event.key == pygame.K_BACKSPACE:
            self.join_host_text = self.join_host_text[:-1]
            return
        if event.unicode and len(self.join_host_text) < 32:
            allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
            if all(ch in allowed for ch in event.unicode):
                self.join_host_text += event.unicode

    def screen_to_cell(self, sx: int, sy: int) -> tuple[int, int] | None:
        if not self.map_view_rect.collidepoint(sx, sy):
            return None
        x = int((sx - self.camera_x) / self.scale)
        y = int((sy - self.camera_y) / self.scale)
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(x), int(y)
        return None

    def cell_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return int(self.camera_x + x * self.scale), int(self.camera_y + y * self.scale)

    def open_context_menu(self, sx: int, sy: int, x: int, y: int) -> None:
        options = [
            ("상륙공격", "amphib"),
            ("공중공격: 전투기", "fighter"),
            ("공중공격: 폭격기", "bomber"),
            ("탄도미사일", "ballistic"),
            ("핵탄도미사일", "nuke"),
            ("전투함 배치", "ship"),
        ]
        if self.owner[x][y] == PLAYER_ID:
            options.append(("건설", "build"))
        menu_h = 34 + len(options) * 30
        self.menu = Menu(min(sx, self.map_view_rect.right - 170), min(sy, SCREEN_H - menu_h - 6), x, y, options)

    def click_menu(self, mx: int, my: int) -> bool:
        assert self.menu
        for i, (_, action) in enumerate(self.menu.options):
            rect = pygame.Rect(self.menu.x, self.menu.y + 28 + i * 30, 160, 28)
            if rect.collidepoint(mx, my):
                x, y = self.menu.map_x, self.menu.map_y
                self.menu = None
                if action == "build":
                    self.open_build_menu(mx, my, x, y)
                else:
                    self.execute_action(action, x, y)
                return True
        return False

    def open_build_menu(self, sx: int, sy: int, x: int, y: int) -> None:
        options = [
            ("공군기지", "build_airbase"),
            ("공장", "build_factory"),
            ("보급로", "build_supply"),
            ("항구", "build_port"),
            ("도시", "build_city"),
            ("도시 레벨업", "upgrade_city"),
            ("방공미사일기지", "build_sam"),
        ]
        self.menu = Menu(
            min(sx, self.map_view_rect.right - 190),
            min(sy, SCREEN_H - (34 + len(options) * 30) - 6),
            x,
            y,
            options,
            "건설",
        )

    def execute_action(self, action: str, x: int, y: int) -> None:
        if action == "amphib":
            self.amphibious_attack(x, y)
        elif action == "fighter":
            self.launch_air(x, y, "fighter")
        elif action == "bomber":
            self.launch_air(x, y, "bomber")
        elif action == "ballistic":
            self.launch_ballistic(x, y, nuclear=False)
        elif action == "nuke":
            self.launch_ballistic(x, y, nuclear=True)
        elif action == "ship":
            self.deploy_ship(x, y)
        elif action.startswith("build_") or action == "upgrade_city":
            self.build(action, x, y)

    def update(self, dt: float) -> None:
        self.update_camera(dt)
        self.update_online_status()
        if self.screen_mode == "lobby":
            return
        if self.screen_mode == "matching":
            self.update_matching(dt)
            return
        if self.paused:
            return
        if self.choosing_capital or self.game_over:
            return
        if self.multiplayer_speed_locked() and self.sim_speed != 1.0:
            self.sim_speed = 1.0
        sim_dt = dt * self.sim_speed
        self.update_build_cooldowns(sim_dt)
        self.update_weapon_cooldowns(sim_dt)
        self.update_economy(sim_dt)
        self.ensure_supply_networks()
        self.update_supply_collapse(sim_dt)
        self.update_fallout(sim_dt)
        self.update_attacks(sim_dt)
        self.update_ai(sim_dt)
        self.update_units(sim_dt)
        self.update_alive()
        self.update_game_end(sim_dt)
        self.update_autosave(sim_dt)

    def update_matching(self, dt: float) -> None:
        if self.online_lobby_active() and not self.online_ready_to_start():
            ready = len(self.online_ready_players())
            total = len(self.online_players())
            self.match_timer = 0.0
            self.match_found = max(0, total - 1)
            self.status = f"온라인 매칭 대기: READY {ready}/{total}"
            return
        self.match_timer += dt
        progress = min(1.0, self.match_timer / self.match_duration)
        online_count = max(0, len(self.online_players()) - 1)
        self.match_found = min(self.ai_count, max(online_count, int(progress * self.ai_count)))
        if self.online_lobby_active():
            self.status = f"온라인 매칭 중: 준비 {len(self.online_ready_players())}/{len(self.online_players())}, AI {self.match_found}/{self.ai_count}"
        else:
            self.status = f"매칭 중: AI {self.match_found}/{self.ai_count}"
        if progress >= 1.0:
            self.start_matched_game()

    def start_matchmaking(self) -> None:
        if self.online_lobby_active() and not self.online_ready_to_start():
            ready = len(self.online_ready_players())
            total = len(self.online_players())
            self.status = f"매칭 시작 불가: 모든 온라인 참가자가 READY여야 합니다 ({ready}/{total})"
            return
        self.screen_mode = "matching"
        self.match_timer = 0.0
        self.match_found = max(0, len(self.online_players()) - 1)
        self.menu = None
        self.show_help = False
        if self.online_lobby_active():
            ready = len(self.online_ready_players())
            total = len(self.online_players())
            self.status = f"온라인 로비 매칭 시작: 준비 {ready}/{total}"
        else:
            self.status = "매칭 시작: 참가자 찾는 중"

    def start_matched_game(self) -> None:
        self.screen_mode = "game"
        self.match_found = self.ai_count
        self.choosing_capital = True
        self.show_help = True
        if self.online_lobby_active():
            self.status = "온라인 로비 매칭 완료: 전투는 아직 로컬 시뮬레이션입니다"
        else:
            self.status = f"매칭 완료: {self.ai_count + 1}명 입장, 수도를 선택하세요"

    def return_to_lobby(self) -> None:
        self.screen_mode = "lobby"
        self.show_help = False
        self.menu = None
        self.load_random_map()
        self.screen_mode = "lobby"
        self.paused = False
        self.status = "로비: 매칭 시작을 누르세요"

    def toggle_pause(self) -> None:
        if self.screen_mode != "game" or self.game_over:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_menu_page = "main"
        self.status = "일시정지" if self.paused else "게임 재개"

    def toggle_building_display(self) -> None:
        self.show_buildings = not self.show_buildings
        self.status = f"건물 표시 {'켜짐' if self.show_buildings else '꺼짐'}"

    def toggle_support_zones(self) -> None:
        modes = ["off", "outline", "full"]
        current_index = modes.index(self.show_support_zones) if self.show_support_zones in modes else 0
        self.show_support_zones = modes[(current_index + 1) % len(modes)]
        self.status = f"보급 레이어: {self.support_zones_label()}"

    def toggle_owner_borders(self) -> None:
        self.show_owner_borders = not self.show_owner_borders
        self.status = f"테두리만 표시 {'켜짐' if self.show_owner_borders else '꺼짐'}"

    def toggle_ai_traits(self) -> None:
        self.show_ai_traits = not self.show_ai_traits
        self.status = f"AI 성향 표시 {'켜짐' if self.show_ai_traits else '꺼짐'}"

    def toggle_operation_info(self) -> None:
        self.show_operation_info = not self.show_operation_info
        self.status = f"작전 레이어 {'켜짐' if self.show_operation_info else '꺼짐'}"

    def toggle_territory_images(self) -> None:
        self.territory_images_enabled = not self.territory_images_enabled
        if self.territory_images_enabled:
            self.load_territory_images()
            self.rebuild_owner_overlay()
        self.status = f"영토 이미지 {'켜짐' if self.territory_images_enabled else '꺼짐'}"

    def cycle_territory_image(self, direction: int = 1) -> None:
        self.load_territory_images()
        if not self.territory_image_files:
            self.status = "영토 이미지 파일 없음"
            return
        names = [path.name for path in self.territory_image_files]
        index = names.index(self.territory_image_file) if self.territory_image_file in names else 0
        self.territory_image_file = names[(index + direction) % len(names)]
        self.load_territory_images()
        self.rebuild_owner_overlay()
        self.status = f"영토 이미지 선택: {self.territory_image_file}"

    def cycle_territory_image_mode(self) -> None:
        keys = [key for key, _label in TERRITORY_IMAGE_MODES]
        index = keys.index(self.territory_image_mode) if self.territory_image_mode in keys else 0
        self.territory_image_mode = keys[(index + 1) % len(keys)]
        self.rebuild_owner_overlay()
        self.status = f"영토 이미지 방식: {self.territory_image_mode_label()}"

    def upload_territory_image(self) -> None:
        try:
            from tkinter import Tk, filedialog

            root = Tk()
            root.withdraw()
            file_name = filedialog.askopenfilename(
                title="영토 이미지 선택",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All files", "*.*")],
            )
            root.destroy()
        except Exception as exc:
            self.status = f"이미지 업로드 실패: {exc}"
            return
        if not file_name:
            self.status = "이미지 업로드 취소"
            return
        source = Path(file_name)
        TERRITORY_IMAGE_DIR.mkdir(exist_ok=True)
        target = TERRITORY_IMAGE_DIR / source.name
        if target.exists():
            target = TERRITORY_IMAGE_DIR / f"{source.stem}_{datetime.now().strftime('%H%M%S')}{source.suffix}"
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            self.status = f"이미지 복사 실패: {exc}"
            return
        self.territory_image_file = target.name
        self.territory_images_enabled = True
        self.load_territory_images()
        self.rebuild_owner_overlay()
        self.status = f"영토 이미지 업로드: {target.name}"

    def change_sim_speed(self, direction: int) -> None:
        if self.multiplayer_speed_locked():
            self.sim_speed = 1.0
            self.status = "온라인 참가자가 있어 배속 비활성화"
            return
        speeds = [0.5, 1.0, 2.0, 4.0]
        index = min(range(len(speeds)), key=lambda i: abs(speeds[i] - self.sim_speed))
        index = max(0, min(len(speeds) - 1, index + direction))
        self.sim_speed = speeds[index]
        self.status = f"게임 속도 {self.sim_speed:g}x"

    def multiplayer_speed_locked(self) -> bool:
        return len(self.online_players()) > 1

    def cycle_map_size(self, direction: int = 1) -> None:
        keys = [key for key, _label, _max_dim in MAP_SIZE_OPTIONS]
        index = keys.index(self.map_size_key) if self.map_size_key in keys else keys.index(DEFAULT_MAP_SIZE_KEY)
        self.map_size_key = keys[(index + direction) % len(keys)]
        self.load_map(self.map_index)
        self.screen_mode = "lobby"
        self.status = f"맵 크기: {self.map_size_label()}"

    def cycle_ai_count(self, direction: int = 1) -> None:
        index = AI_COUNT_OPTIONS.index(self.ai_count) if self.ai_count in AI_COUNT_OPTIONS else 1
        self.ai_count = AI_COUNT_OPTIONS[(index + direction) % len(AI_COUNT_OPTIONS)]
        self.load_map(self.map_index)
        self.screen_mode = "lobby"
        self.status = f"{self.ai_count_label()}: AI {self.ai_count}명"

    def cycle_pace(self, direction: int = 1) -> None:
        keys = [str(option["key"]) for option in PACE_OPTIONS]
        index = keys.index(self.pace_key) if self.pace_key in keys else 0
        self.pace_key = keys[(index + direction) % len(keys)]
        self.load_map(self.map_index)
        self.screen_mode = "lobby"
        self.status = f"전략 템포: {self.pace_label()} - {self.pace_description()}"

    def host_online_lobby(self) -> None:
        if self.online_server is None or not self.online_server.running:
            self.online_server = OnlineMatchServer(port=DEFAULT_PORT)
            if not self.online_server.start():
                self.online_status = f"온라인 방 생성 실패: {self.online_server.error}"
                self.status = self.online_status
                self.online_server = None
                return
            self.online_host_hint = local_ip_hint()
        self.join_online_lobby("127.0.0.1", name="Host")
        self.online_status = f"온라인 방 생성: {self.online_host_hint}:{DEFAULT_PORT}"
        self.status = self.online_status

    def join_online_lobby(self, host: str, name: str = "Player") -> None:
        if self.online_client:
            self.online_client.close()
        self.online_ready = False
        self.online_client = OnlineMatchClient(host=host, port=DEFAULT_PORT, name=name)
        if self.online_client.connect():
            self.online_status = f"온라인 로비 연결: {host}:{DEFAULT_PORT}"
        else:
            self.online_status = self.online_client.state.message
        self.status = self.online_status

    def disconnect_online(self) -> None:
        if self.online_client:
            self.online_client.close()
        if self.online_server:
            self.online_server.stop()
        self.online_client = None
        self.online_server = None
        self.online_host_hint = local_ip_hint()
        self.online_ready = False
        self.online_status = "온라인: 연결 안 됨"
        self.status = "온라인 연결 해제"

    def toggle_online_ready(self) -> None:
        if not self.online_client or not self.online_client.state.connected:
            self.status = "준비 실패: 온라인 로비에 연결되어 있지 않음"
            return
        self.online_ready = not self.online_ready
        self.online_client.send({"type": "ready", "ready": self.online_ready})
        self.status = "온라인 준비 완료" if self.online_ready else "온라인 준비 취소"

    def shutdown_online(self) -> None:
        if self.online_client:
            self.online_client.close()
        if self.online_server:
            self.online_server.stop()

    def update_online_status(self) -> None:
        if self.online_client:
            self.online_status = self.online_client.state.message
            if not self.online_client.state.connected and not self.online_client.running:
                self.online_ready = False
                self.online_status = self.online_client.state.message or "온라인: 연결 끊김"

    def online_players(self) -> list[str]:
        if self.online_client:
            return self.online_client.state.players
        return []

    def online_ready_players(self) -> list[str]:
        if self.online_client:
            return self.online_client.state.ready_players
        return []

    def online_lobby_active(self) -> bool:
        return bool(self.online_client and self.online_client.state.connected)

    def online_ready_to_start(self) -> bool:
        players = self.online_players()
        if not players:
            return False
        ready = set(self.online_ready_players())
        return bool(players) and all(name in ready for name in players)

    def update_build_cooldowns(self, dt: float) -> None:
        expired = []
        for owner, remaining in self.build_cooldowns.items():
            remaining = max(0.0, remaining - dt)
            if remaining <= 0:
                expired.append(owner)
            else:
                self.build_cooldowns[owner] = remaining
        for owner in expired:
            self.build_cooldowns.pop(owner, None)

    def update_weapon_cooldowns(self, dt: float) -> None:
        for faction in self.factions:
            faction.ballistic_cooldown = max(0.0, faction.ballistic_cooldown - dt)
            faction.nuke_cooldown = max(0.0, faction.nuke_cooldown - dt)

    def update_autosave(self, dt: float) -> None:
        if self.choosing_capital or self.game_over:
            return
        self.autosave_timer += dt
        if self.autosave_timer >= AUTOSAVE_INTERVAL:
            self.autosave_timer = 0.0
            self.save_game(autosave=True)

    def update_camera(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        speed = 520 * dt
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed *= 1.8
        if keys[pygame.K_a]:
            self.camera_x += speed
        if keys[pygame.K_d]:
            self.camera_x -= speed
        if keys[pygame.K_w]:
            self.camera_y += speed
        if keys[pygame.K_s]:
            self.camera_y -= speed
        self.clamp_camera()

    def zoom_at(self, sx: int, sy: int, factor: float) -> None:
        before_x = (sx - self.camera_x) / self.scale
        before_y = (sy - self.camera_y) / self.scale
        self.scale = max(self.base_scale * 0.65, min(self.base_scale * 5.0, self.scale * factor))
        self.rebuild_map_surface()
        self.camera_x = sx - before_x * self.scale
        self.camera_y = sy - before_y * self.scale
        self.clamp_camera()

    def clamp_camera(self) -> None:
        scaled_w = self.width * self.scale
        scaled_h = self.height * self.scale
        if scaled_w <= self.map_view_rect.w:
            self.camera_x = (self.map_view_rect.w - scaled_w) / 2
        else:
            self.camera_x = min(0, max(self.map_view_rect.w - scaled_w, self.camera_x))
        if scaled_h <= self.map_view_rect.h:
            self.camera_y = (self.map_view_rect.h - scaled_h) / 2
        else:
            self.camera_y = min(0, max(self.map_view_rect.h - scaled_h, self.camera_y))

    def update_economy(self, dt: float) -> None:
        interval_multiplier = float(self.pace_option()["economy_interval_multiplier"])
        city_interval = 2.5 * interval_multiplier
        port_interval = 4.0 * interval_multiplier
        for building in self.buildings:
            building.timer += dt
            if building.kind == "city" and building.timer >= city_interval:
                building.timer = 0
                faction = self.factions[building.owner]
                faction.money += 9 * building.level
                faction.troops += 18 * building.level
                self.clamp_faction_troops(building.owner)
            elif building.kind == "port" and building.timer >= port_interval:
                building.timer = 0
                self.factions[building.owner].money += 18

    def mark_supply_dirty(self) -> None:
        self.supply_dirty = True

    def ensure_supply_networks(self) -> None:
        if self.supply_dirty:
            self.rebuild_supply_networks()

    def rebuild_supply_networks(self) -> None:
        factories: dict[int, set[tuple[int, int]]] = {}
        roads: dict[int, set[tuple[int, int]]] = {}
        for building in self.buildings:
            if building.kind == "factory":
                factories.setdefault(building.owner, set()).add((building.x, building.y))
            elif building.kind == "supply":
                roads.setdefault(building.owner, set()).add((building.x, building.y))

        active: dict[int, list[tuple[int, int]]] = {}
        ranges: dict[int, dict[tuple[int, int], int]] = {}
        links: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
        for owner, factory_cells in factories.items():
            active_set = set(factory_cells)
            owner_ranges = {cell: SUPPLY_FACTORY_RANGE for cell in factory_cells}
            owner_roads = roads.get(owner, set())
            owner_links: list[tuple[tuple[int, int], tuple[int, int]]] = []
            queue = deque(factory_cells)
            while queue:
                x, y = queue.popleft()
                for nxt in list(owner_roads - active_set):
                    if self.supply_linked((x, y), nxt):
                        active_set.add(nxt)
                        owner_ranges[nxt] = SUPPLY_RANGE
                        owner_links.append(((x, y), nxt))
                        queue.append(nxt)
            active[owner] = list(active_set)
            ranges[owner] = owner_ranges
            links[owner] = owner_links
        self.active_supply_sources = active
        self.active_supply_ranges = ranges
        self.active_supply_links = links
        self.supply_dirty = False

    def supply_linked(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        ax, ay = a
        bx, by = b
        return (ax - bx) * (ax - bx) + (ay - by) * (ay - by) <= SUPPLY_RANGE * SUPPLY_RANGE

    def in_supply_range(self, owner: int, x: int, y: int) -> bool:
        self.ensure_supply_networks()
        ranges = self.active_supply_ranges.get(owner, {})
        return any((x - sx) * (x - sx) + (y - sy) * (y - sy) <= radius * radius for (sx, sy), radius in ranges.items())

    def has_active_supply(self, fid: int) -> bool:
        self.ensure_supply_networks()
        return bool(self.active_supply_sources.get(fid))

    def update_supply_collapse(self, dt: float) -> None:
        for fid, faction in enumerate(self.factions):
            if not faction.alive or self.territory_counts[fid] <= 0:
                faction.unsupplied_time = 0
                faction.unsupplied_start_troops = None
                continue
            if self.has_active_supply(fid):
                faction.unsupplied_time = 0
                faction.unsupplied_start_troops = None
                continue
            if faction.unsupplied_start_troops is None:
                faction.unsupplied_start_troops = faction.troops
                faction.unsupplied_time = 0
            faction.unsupplied_time += dt
            ratio = max(SUPPLY_COLLAPSE_FLOOR, 1 - faction.unsupplied_time / SUPPLY_COLLAPSE_TIME)
            faction.troops = min(faction.troops, math.floor(faction.unsupplied_start_troops * ratio))
            if fid == PLAYER_ID and faction.troops > 0:
                self.status = "보급망 상실: 병력이 천천히 약화 중"

    def update_attacks(self, dt: float) -> None:
        active_operations: list[Operation] = []
        for operation in self.operations:
            faction = self.factions[operation.owner]
            if not faction.alive or operation.troops <= 0 or operation.target == operation.owner:
                self.refund_operation_troops(operation)
                continue
            operation.age += dt
            if operation.owner != PLAYER_ID:
                operation.timer += dt
                if operation.timer < float(self.pace_option()["attack_interval"]):
                    active_operations.append(operation)
                    continue
                operation.timer = 0
            self.advance_front(operation)
            if operation.finished:
                self.refund_operation_troops(operation)
            elif operation.troops > 0:
                active_operations.append(operation)
            else:
                self.status = f"{operation.label} 종료: 병력 소진"
        self.operations = active_operations

    def refund_operation_troops(self, operation: Operation) -> None:
        if operation.troops <= 0 or not self.factions[operation.owner].alive:
            operation.troops = 0
            return
        faction = self.factions[operation.owner]
        before = faction.troops
        faction.troops += operation.troops
        self.clamp_faction_troops(operation.owner)
        returned = faction.troops - before
        operation.troops = 0
        if operation.owner == PLAYER_ID and returned > 0:
            self.status = f"{operation.label} 종료: 잔여 병력 {returned}명 복귀"

    def create_operation(
        self,
        owner: int,
        target: int | None,
        troops: int,
        label: str,
        cells: set[tuple[int, int]] | None = None,
        focus: tuple[int, int] | None = None,
        supply_grace: float = 0.0,
        reserve_troops: bool = True,
    ) -> bool:
        faction = self.factions[owner]
        if target == owner:
            if owner == PLAYER_ID:
                self.status = "작전 취소: 자신의 땅은 공격 대상이 아님"
            return False
        troops = min(troops, faction.troops) if reserve_troops else troops
        if troops <= 0:
            if owner == PLAYER_ID:
                self.status = "작전 실패: 투입 가능한 병력이 없음"
            return False
        if reserve_troops:
            faction.troops -= troops
        operation = Operation(owner, target, troops, label=label, cells=cells, focus=focus, supply_grace=supply_grace)
        self.operations.append(operation)
        if target is not None and target != owner:
            self.wars.add(frozenset((owner, target)))
            war = f" / 전쟁 상태: {faction.name} vs {self.factions[target].name}"
        else:
            war = ""
        if owner == PLAYER_ID:
            self.status = f"{label}: {self.target_name(target)}에 {troops}명 투입{war}"
        return True

    def advance_front(self, operation: Operation) -> None:
        fid = operation.owner
        candidates = self.operation_candidates(operation)
        if not candidates:
            operation.finished = True
            return
        candidates = self.choose_attack_candidates(candidates, operation)
        attacks = 0
        for x, y in candidates:
            if attacks >= ATTACKS_PER_FRAME:
                break
            if not self.terrain_allows_advance(x, y):
                continue
            cost = self.attack_troop_cost(fid, x, y)
            if operation.troops < cost:
                continue
            operation.troops -= cost
            attacks += 1
            if self.resolve_pixel_attack(fid, x, y, cost) and operation.cells is not None:
                operation.cells.add((x, y))
        if attacks == 0 and candidates and all(self.attack_troop_cost(fid, x, y) > operation.troops for x, y in candidates):
            operation.finished = True

    def terrain_allows_advance(self, x: int, y: int) -> bool:
        terrain = self.terrain[x][y] if 0 <= x < self.width and 0 <= y < self.height else "plain"
        speed = TERRAIN_SPEED.get(terrain, 1.0)
        return speed >= 1.0 or random.random() < speed

    def attack_troop_cost(self, attacker: int, x: int, y: int) -> int:
        defender = self.owner[x][y]
        if defender is None or defender == attacker:
            return PIXEL_ATTACK_COST
        if self.factions[defender].troops <= NO_RESISTANCE_TROOPS:
            return 0
        density = self.factions[defender].troops / max(1, self.territory_counts[defender])
        scaled = math.ceil(self.factions[defender].troops * ENEMY_TROOP_COST_RATIO + density * ENEMY_DENSITY_COST_RATIO)
        return max(PIXEL_ATTACK_COST, min(MAX_ATTACK_COST, scaled))

    def choose_attack_candidates(self, candidates: list[tuple[int, int]], operation: Operation) -> list[tuple[int, int]]:
        if not candidates:
            return []
        scored = [(self.attack_score(cell, operation), cell) for cell in candidates]
        scored.sort(key=lambda item: item[0])
        selected: list[tuple[int, int]] = []
        used: set[tuple[int, int]] = set()
        bucket_size = max(ATTACKS_PER_FRAME * 3, 18)
        for bucket_start in range(0, min(len(scored), bucket_size * 3), bucket_size):
            bucket = [cell for _, cell in scored[bucket_start : bucket_start + bucket_size]]
            random.shuffle(bucket)
            for cell in bucket:
                if cell in used:
                    continue
                if selected and sum(1 for other in selected if abs(cell[0] - other[0]) + abs(cell[1] - other[1]) <= 1) >= 2:
                    continue
                selected.append(cell)
                used.add(cell)
                if len(selected) >= ATTACKS_PER_FRAME:
                    return selected
        for _, cell in scored:
            if cell not in used:
                selected.append(cell)
                if len(selected) >= ATTACKS_PER_FRAME:
                    break
        return selected

    def sort_attack_candidates(self, candidates: list[tuple[int, int]], operation: Operation) -> None:
        candidates.sort(key=lambda cell: self.attack_score(cell, operation))

    def attack_score(self, cell: tuple[int, int], operation: Operation) -> float:
        x, y = cell
        support = sum(
            1
            for dx, dy in NEIGHBORS
            if 0 <= x + dx < self.width and 0 <= y + dy < self.height and self.owner[x + dx][y + dy] == operation.owner
        )
        shape = -support * 5
        if operation.focus is None:
            return shape + random.random() * 0.05
        fx, fy = operation.focus
        distance = abs(x - fx) + abs(y - fy)
        return distance + shape + random.random() * 0.05

    def operation_candidates(self, operation: Operation) -> list[tuple[int, int]]:
        fid = operation.owner
        target = operation.target
        if operation.cells is None:
            return [cell for cell in self.frontiers[fid] if self.can_attack_cell(cell[0], cell[1], target, fid, operation)]
        candidates: set[tuple[int, int]] = set()
        for x, y in operation.cells:
            if not (0 <= x < self.width and 0 <= y < self.height) or self.owner[x][y] != fid:
                continue
            for dx, dy in NEIGHBORS:
                nx, ny = x + dx, y + dy
                if self.can_attack_cell(nx, ny, target, fid, operation):
                    candidates.add((nx, ny))
        return list(candidates)

    def can_attack_cell(self, x: int, y: int, target: int | None, fid: int, operation: Operation | None = None) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height) or not self.land[x][y]:
            return False
        current = self.owner[x][y]
        if current == fid:
            return False
        temporary_supply = operation is not None and operation.age < operation.supply_grace
        if not temporary_supply and not self.in_supply_range(fid, x, y):
            return False
        if target is None:
            return current is None
        return current == target

    def resolve_pixel_attack(self, fid: int, x: int, y: int, power: int) -> bool:
        defender = self.owner[x][y]
        if defender is None:
            self.set_owner(x, y, fid)
            return True
        if self.factions[defender].troops <= NO_RESISTANCE_TROOPS:
            self.set_owner(x, y, fid)
            self.transfer_buildings_at(x, y, fid)
            return True
        defense = 10 + len(self.buildings_at(x, y)) * 10
        attack_value = max(1, power)
        if random.random() < attack_value / (attack_value + defense):
            self.factions[defender].troops = max(0, self.factions[defender].troops - power)
            self.set_owner(x, y, fid)
            self.transfer_buildings_at(x, y, fid)
            return True
        else:
            self.factions[defender].troops = max(0, self.factions[defender].troops - power // 2)
        return False

    def update_ai(self, dt: float) -> None:
        self.ai_decision_timer += dt
        if self.ai_decision_timer < float(self.pace_option()["ai_decision_interval"]):
            return
        self.ai_decision_timer = 0
        chance_multiplier = float(self.pace_option()["ai_chance_multiplier"])
        active_by_owner: dict[int, int] = {}
        for op in self.operations:
            active_by_owner[op.owner] = active_by_owner.get(op.owner, 0) + 1
        for fid, faction in enumerate(self.factions):
            if fid == PLAYER_ID or not faction.alive:
                continue
            personality = AI_PERSONALITIES[faction.personality]
            active_count = active_by_owner.get(fid, 0)
            nearby_enemies = [owner for owner in self.neighbor_owners(fid) if owner not in {None, fid}]
            if active_count < personality["max_operations"] and random.random() < personality["operation_chance"] * chance_multiplier:
                target = self.ai_attack_target_owner(fid)
                troops = int(personality["operation_troops"] * max(0.75, chance_multiplier))
                if target != fid and self.create_operation(fid, target, troops, "AI 작전"):
                    active_by_owner[fid] = active_by_owner.get(fid, 0) + 1
            elif not nearby_enemies and active_count < 1 and random.random() < 0.012 * chance_multiplier:
                troops = max(70, int(personality["operation_troops"] * 0.45))
                if self.create_operation(fid, None, troops, "AI 개척"):
                    active_by_owner[fid] = active_by_owner.get(fid, 0) + 1
            if random.random() < personality["air_chance"] * chance_multiplier:
                self.ai_air_attack(fid)
            if random.random() < personality["ballistic_chance"] * chance_multiplier:
                self.ai_ballistic_attack(fid)
            if random.random() < personality["build_chance"] * chance_multiplier and faction.money >= 130:
                self.ai_build(fid)

    def ai_air_attack(self, fid: int) -> None:
        faction = self.factions[fid]
        if faction.money < 90:
            return
        launch_sites = [b for b in self.buildings if b.owner == fid and b.kind == "airbase"]
        if not launch_sites:
            return
        target_owner = self.ai_attack_target_owner(fid)
        target_cell = self.random_target_cell(target_owner, strategic=True)
        if target_cell is None:
            return
        base = min(launch_sites, key=lambda b: abs(b.x - target_cell[0]) + abs(b.y - target_cell[1]))
        faction.money -= 90
        self.units.append(
            Unit(
                "bomber",
                fid,
                base.x,
                base.y,
                target_cell[0],
                target_cell[1],
                source=(base.x, base.y),
                target_cell=target_cell,
                speed=64,
                operation_target=target_owner,
            )
        )
        if target_owner is not None and target_owner != fid:
            self.wars.add(frozenset((fid, target_owner)))

    def ai_ballistic_attack(self, fid: int) -> None:
        faction = self.factions[fid]
        if faction.money < BALLISTIC_COST:
            return
        if not any(b.owner == fid and b.kind == "airbase" for b in self.buildings):
            return
        target_owner = self.ai_attack_target_owner(fid)
        if target_owner is None or target_owner == fid:
            return
        target_cell = self.random_target_cell(target_owner, strategic=True)
        if target_cell is None:
            return
        if self.launch_ballistic(target_cell[0], target_cell[1], nuclear=False, owner=fid):
            if target_owner != fid:
                self.wars.add(frozenset((fid, target_owner)))

    def ai_attack_target_owner(self, fid: int) -> int | None:
        neighbors = [owner for owner in self.neighbor_owners(fid) if owner != fid]
        enemies = [owner for owner in neighbors if owner is not None]
        if enemies:
            own_land = max(1, self.territory_counts[fid])
            own_troops = max(1, self.factions[fid].troops)
            scored: list[tuple[float, int]] = []
            for enemy in enemies:
                enemy_land = max(1, self.territory_counts[enemy])
                enemy_troops = max(1, self.factions[enemy].troops)
                score = 1.0
                score += min(1.2, enemy_land / own_land * 0.45)
                score += min(0.8, enemy_troops / own_troops * 0.25)
                if enemy == PLAYER_ID:
                    score *= 1.03
                if enemy_land <= ENEMY_SURVIVOR_PIXEL_LIMIT:
                    score *= 0.35
                score *= random.uniform(0.85, 1.15)
                scored.append((score, enemy))
            scored.sort(reverse=True)
            return scored[0][1]
        return None

    def neighbor_owners(self, fid: int) -> list[int | None]:
        found: set[int | None] = set()
        for x, y in self.frontiers[fid]:
            found.add(self.owner[x][y])
        return list(found)

    def random_target_cell(self, target: int | None, strategic: bool = False) -> tuple[int, int] | None:
        if strategic and target is not None:
            priority = [
                (b.x, b.y)
                for b in self.buildings
                if b.owner == target and b.kind in {"factory", "supply", "airbase", "sam"}
            ]
            if priority and random.random() < 0.42:
                return random.choice(priority)
        attempts = min(700, max(80, self.width * self.height // 28))
        for _ in range(attempts):
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self.land[x][y] and self.owner[x][y] == target:
                return x, y

        chosen: tuple[int, int] | None = None
        seen = 0
        for x in range(self.width):
            for y in range(self.height):
                if self.land[x][y] and self.owner[x][y] == target:
                    seen += 1
                    if random.randrange(seen) == 0:
                        chosen = (x, y)
        return chosen

    def ai_build(self, fid: int) -> None:
        if self.build_cooldowns.get(fid, 0.0) > 0:
            return
        cells = self.ai_build_candidates(fid)
        if not cells:
            return
        personality = AI_PERSONALITIES[self.factions[fid].personality]
        kind = random.choice(personality["build_choices"])
        if not any(b.owner == fid and b.kind == "factory" for b in self.buildings):
            kind = "factory"
        elif (
            self.territory_counts[fid] >= 45
            and sum(1 for b in self.buildings if b.owner == fid and b.kind == "supply") < max(1, self.territory_counts[fid] // 95)
        ):
            kind = "supply"
        x, y = self.ai_build_site(fid, kind, cells)
        if self.buildings_at(x, y):
            return
        if kind == "port" and not self.is_coast(x, y):
            kind = "city"
        costs = {"factory": 260, "supply": 35, "city": 120, "port": 130, "airbase": 170, "sam": 150}
        cost = costs.get(kind, 130)
        if self.factions[fid].money < cost:
            return
        self.factions[fid].money -= cost
        self.buildings.append(Building(kind, fid, x, y))
        self.build_cooldowns[fid] = BUILD_COOLDOWN
        if kind in {"factory", "supply"}:
            self.mark_supply_dirty()

    def ai_build_candidates(self, fid: int) -> list[tuple[int, int]]:
        occupied = {(b.x, b.y) for b in self.buildings}
        candidates: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        attempts = min(260, max(60, self.territory_counts[fid] * 4))
        for _ in range(attempts):
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            cell = (x, y)
            if cell not in seen and self.owner[x][y] == fid and cell not in occupied:
                candidates.append(cell)
                seen.add(cell)
                if len(candidates) >= 70:
                    return candidates
        if candidates:
            return candidates
        for x in range(self.width):
            for y in range(self.height):
                cell = (x, y)
                if self.owner[x][y] == fid and cell not in occupied:
                    candidates.append(cell)
                    if len(candidates) >= 70:
                        return candidates
        return candidates

    def ai_build_site(self, fid: int, kind: str, cells: list[tuple[int, int]]) -> tuple[int, int]:
        if kind == "supply":
            self.ensure_supply_networks()
            frontier = self.frontiers[fid]
            source_set = set(self.active_supply_sources.get(fid, []))
            candidates = [
                cell
                for cell in cells
                if self.in_supply_range(fid, cell[0], cell[1]) and cell not in source_set
            ]
            if candidates:
                return min(
                    random.sample(candidates, min(45, len(candidates))),
                    key=lambda cell: min((abs(cell[0] - fx) + abs(cell[1] - fy) for fx, fy in frontier), default=0),
                )
        if kind == "factory":
            center_x = sum(x for x, _y in cells) / max(1, len(cells))
            center_y = sum(y for _x, y in cells) / max(1, len(cells))
            return min(random.sample(cells, min(35, len(cells))), key=lambda cell: abs(cell[0] - center_x) + abs(cell[1] - center_y))
        return random.choice(cells)

    def update_units(self, dt: float) -> None:
        remaining = []
        for unit in self.units:
            dx, dy = unit.tx - unit.x, unit.ty - unit.y
            dist = math.hypot(dx, dy)
            if dist <= unit.speed * dt:
                unit.x, unit.y = unit.tx, unit.ty
                keep_unit = self.unit_arrived(unit)
                if keep_unit or unit.kind == "ship":
                    remaining.append(unit)
            else:
                unit.x += dx / dist * unit.speed * dt
                unit.y += dy / dist * unit.speed * dt
                remaining.append(unit)
        self.units = [u for u in remaining if self.unit_valid(u)]

    def unit_arrived(self, unit: Unit) -> bool:
        if unit.path:
            next_x, next_y = unit.path.pop(0)
            unit.tx, unit.ty = next_x, next_y
            return True
        if unit.kind == "landing" and unit.target_cell:
            if unit.payload <= 0:
                self.status = "상륙 실패: 상륙선이 침몰함"
                return False
            x, y = unit.target_cell
            if not self.land[x][y]:
                fallback = self.closest_coast(x, y)
                if fallback:
                    unit.target_cell = fallback
                    unit.tx, unit.ty = fallback
                    return True
            self.set_owner(x, y, unit.owner)
            self.transfer_buildings_at(x, y, unit.owner)
            self.create_operation(
                unit.owner,
                unit.operation_target,
                max(0, unit.payload),
                "상륙 작전",
                cells={(x, y)},
                focus=unit.target_cell,
                supply_grace=TEMP_OPERATION_GRACE,
                reserve_troops=False,
            )
            self.status = "상륙 성공: 교두보 작전 시작"
            return False
        elif unit.kind == "fighter" and not unit.returning and unit.target_cell:
            x, y = unit.target_cell
            if self.air_defense_hits(unit.owner, x, y):
                self.status = "전투기가 방공망에 격추됨"
                return False
            self.set_owner(x, y, unit.owner)
            self.transfer_buildings_at(x, y, unit.owner)
            self.create_operation(unit.owner, unit.operation_target, 80, "전투기 강습 작전", focus=unit.target_cell, supply_grace=TEMP_OPERATION_GRACE)
            self.return_to_source(unit)
            return True
        elif unit.kind == "bomber" and not unit.returning and unit.target_cell:
            x, y = unit.target_cell
            if self.air_defense_hits(unit.owner, x, y):
                self.status = "폭격기가 방공망에 격추됨"
                return False
            self.missile_strike(x, y)
            self.return_to_source(unit)
            return True
        elif unit.kind in {"ballistic", "nuke"} and unit.target_cell:
            x, y = unit.target_cell
            if self.ballistic_intercepted(unit.owner, x, y):
                self.status = "탄도미사일이 방공망에 요격됨"
                return False
            if unit.kind == "nuke":
                self.nuclear_strike(x, y)
            else:
                self.ballistic_strike(x, y)
            return False
        return False

    def unit_valid(self, unit: Unit) -> bool:
        if unit.kind != "ship":
            return True
        for other in self.units:
            if other.kind == "landing" and other.owner != unit.owner:
                if math.hypot(other.x - unit.x, other.y - unit.y) < 7:
                    other.payload = -1
                    return True
        return True

    def return_to_source(self, unit: Unit) -> None:
        if unit.source:
            unit.returning = True
            unit.tx, unit.ty = unit.source
            unit.speed = 58

    def air_defense_hits(self, attacker: int, x: int, y: int) -> bool:
        for building in self.buildings:
            if building.owner == attacker or building.kind != "sam":
                continue
            if abs(building.x - x) + abs(building.y - y) <= 8:
                if random.random() < 0.8:
                    return True
                self.missile_strike(building.x + random.randint(-2, 2), building.y + random.randint(-2, 2))
        return False

    def ballistic_intercepted(self, attacker: int, x: int, y: int) -> bool:
        has_interceptor = any(
            building.owner != attacker
            and building.kind == "sam"
            and abs(building.x - x) + abs(building.y - y) <= 10
            for building in self.buildings
        )
        return has_interceptor and random.random() < BALLISTIC_INTERCEPT_CHANCE

    def missile_strike(self, x: int, y: int) -> None:
        for tx in range(max(0, x - 1), min(self.width, x + 2)):
            for ty in range(max(0, y - 1), min(self.height, y + 2)):
                if self.land[tx][ty]:
                    self.set_owner(tx, ty, None)
                    self.destroy_buildings_at(tx, ty)
        self.status = "미사일 폭격: 건물 파괴 및 빈땅화"

    def ballistic_strike(self, x: int, y: int) -> None:
        if self.land[x][y]:
            self.set_owner(x, y, None)
            self.destroy_buildings_at(x, y)
        for tx in range(max(0, x - 1), min(self.width, x + 2)):
            for ty in range(max(0, y - 1), min(self.height, y + 2)):
                if self.land[tx][ty] and self.buildings_at(tx, ty):
                    self.destroy_buildings_at(tx, ty)
                    self.set_owner(tx, ty, None)
        self.status = "탄도미사일 타격: 중심지와 인접 건물 파괴"

    def nuclear_strike(self, x: int, y: int) -> None:
        radius_sq = NUKE_RADIUS * NUKE_RADIUS
        for tx in range(max(0, x - NUKE_RADIUS), min(self.width, x + NUKE_RADIUS + 1)):
            for ty in range(max(0, y - NUKE_RADIUS), min(self.height, y + NUKE_RADIUS + 1)):
                if not self.land[tx][ty]:
                    continue
                if (tx - x) * (tx - x) + (ty - y) * (ty - y) <= radius_sq:
                    self.set_owner(tx, ty, None)
                    self.destroy_buildings_at(tx, ty)
                    self.fallout[(tx, ty)] = FALLOUT_DURATION
        self.status = "핵탄도미사일 폭발: 반경 30칸 증발 및 낙진 발생"

    def update_fallout(self, dt: float) -> None:
        if not self.fallout:
            self.fallout_timer = 0.0
            return
        self.fallout_timer += dt
        wipe_now = self.fallout_timer >= FALLOUT_TICK_INTERVAL
        if wipe_now:
            self.fallout_timer = 0.0
        expired = []
        for cell, remaining in list(self.fallout.items()):
            remaining -= dt
            if remaining <= 0:
                expired.append(cell)
                continue
            self.fallout[cell] = remaining
            if wipe_now:
                x, y = cell
                if self.owner[x][y] is not None:
                    self.set_owner(x, y, None)
                    self.destroy_buildings_at(x, y)
        for cell in expired:
            self.fallout.pop(cell, None)

    def amphibious_attack(self, x: int, y: int) -> None:
        target_owner = self.owner[x][y]
        self.selected_target = target_owner
        if target_owner == PLAYER_ID:
            self.status = "상륙 실패: 자신의 땅은 상륙 대상이 아님"
            return
        start = self.closest_owned_coast(x, y) or self.closest_launch_coast_from_owned_land(x, y)
        target = self.closest_coast(x, y)
        if not start or not target:
            self.status = "상륙 실패: 출발/목표 해안을 찾지 못함"
            return
        water_path = self.water_path_between_coasts(start, target)
        if not water_path:
            self.status = "상륙 실패: 연결된 바닷길이 없음"
            return
        troops = self.selected_operation_troops()
        if troops <= 0:
            self.status = "상륙 실패: 병력 부족"
            return
        self.factions[PLAYER_ID].troops -= troops
        if target_owner is not None and target_owner != PLAYER_ID:
            self.wars.add(frozenset((PLAYER_ID, target_owner)))
        route = self.compress_water_path(water_path) + [target]
        first_x, first_y = route.pop(0)
        self.units.append(Unit("landing", PLAYER_ID, start[0], start[1], first_x, first_y, target_cell=target, payload=troops, speed=LANDING_SPEED, operation_target=target_owner, path=route))
        self.status = f"상륙작전 출항: {self.target_name(target_owner)}에 {troops}명 투입"

    def launch_air(self, x: int, y: int, kind: str) -> None:
        faction = self.factions[PLAYER_ID]
        airbases = [b for b in self.buildings if b.owner == PLAYER_ID and b.kind == "airbase"]
        if not airbases:
            self.status = "공중공격 실패: 공군기지가 필요함"
            return
        if kind == "fighter" and faction.fighters <= 0:
            self.status = "전투기가 없음. F 키로 구매 가능"
            return
        if kind == "bomber" and faction.bombers <= 0:
            self.status = "폭격기가 없음. B 키로 구매 가능"
            return
        base = min(airbases, key=lambda b: abs(b.x - x) + abs(b.y - y))
        if kind == "fighter":
            faction.fighters -= 1
        else:
            faction.bombers -= 1
        target_owner = self.owner[x][y]
        if target_owner is not None and target_owner != PLAYER_ID:
            self.wars.add(frozenset((PLAYER_ID, target_owner)))
        self.units.append(Unit(kind, PLAYER_ID, base.x, base.y, x, y, source=(base.x, base.y), target_cell=(x, y), speed=64, operation_target=target_owner))
        self.status = "공중공격 출격"

    def launch_ballistic(self, x: int, y: int, nuclear: bool = False, owner: int = PLAYER_ID) -> bool:
        faction = self.factions[owner]
        cost = NUKE_COST if nuclear else BALLISTIC_COST
        cooldown = faction.nuke_cooldown if nuclear else faction.ballistic_cooldown
        if cooldown > 0:
            if owner == PLAYER_ID:
                self.status = f"{'핵' if nuclear else ''}탄도미사일 재장전 중: {cooldown:.0f}초"
            return False
        if faction.money < cost:
            if owner == PLAYER_ID:
                self.status = f"{'핵' if nuclear else ''}탄도미사일 실패: 돈 부족"
            return False
        launch = self.closest_missile_launch_site(owner, x, y)
        if launch is None:
            if owner == PLAYER_ID:
                self.status = "탄도미사일 실패: 공군기지 또는 공장이 필요함"
            return False
        faction.money -= cost
        target_owner = self.owner[x][y]
        kind = "nuke" if nuclear else "ballistic"
        self.units.append(
            Unit(
                kind,
                owner,
                launch[0],
                launch[1],
                x,
                y,
                source=launch,
                target_cell=(x, y),
                speed=BALLISTIC_SPEED,
                operation_target=target_owner,
            )
        )
        if nuclear:
            faction.nuke_cooldown = NUKE_COOLDOWN
            self.add_world_log(f"{faction.name} 핵 발사")
        else:
            faction.ballistic_cooldown = BALLISTIC_COOLDOWN
        if target_owner is not None and target_owner != owner:
            self.wars.add(frozenset((owner, target_owner)))
        if owner == PLAYER_ID:
            name = "핵탄도미사일" if nuclear else "탄도미사일"
            self.status = f"{name} 발사: {self.target_name(target_owner)} 목표"
        return True

    def closest_missile_launch_site(self, owner: int, x: int, y: int) -> tuple[int, int] | None:
        buildings = [b for b in self.buildings if b.owner == owner and b.kind in {"airbase", "factory"}]
        if buildings:
            base = min(buildings, key=lambda b: abs(b.x - x) + abs(b.y - y))
            return base.x, base.y
        return None

    def deploy_ship(self, x: int, y: int) -> None:
        if self.land[x][y]:
            coast = self.closest_water(x, y)
            if coast:
                x, y = coast
        if self.factions[PLAYER_ID].ships <= 0:
            self.status = "전투함이 없음. N 키로 구매 가능"
            return
        self.factions[PLAYER_ID].ships -= 1
        self.units.append(Unit("ship", PLAYER_ID, x, y, x, y, speed=0))
        self.status = "전투함 배치 완료"

    def build(self, action: str, x: int, y: int) -> None:
        if self.owner[x][y] != PLAYER_ID:
            self.status = "건설 실패: 자신의 땅에만 가능"
            return
        cooldown = self.build_cooldowns.get(PLAYER_ID, 0.0)
        if cooldown > 0:
            self.status = f"건설 대기 중: {cooldown:.1f}초"
            return
        costs = {
            "build_airbase": 170,
            "build_factory": 260,
            "build_supply": 35,
            "build_port": 130,
            "build_city": 120,
            "build_sam": 150,
            "upgrade_city": 110,
        }
        cost = costs[action]
        faction = self.factions[PLAYER_ID]
        if faction.money < cost:
            self.status = "건설 실패: 돈 부족"
            return
        if action == "build_port" and not self.is_coast(x, y):
            self.status = "항구는 해변에만 건설 가능"
            return
        if action == "upgrade_city":
            city = next((b for b in self.buildings_at(x, y) if b.kind == "city" and b.level < 5), None)
            if not city:
                self.status = "레벨업 가능한 도시가 없음"
                return
            faction.money -= cost
            city.level += 1
            self.build_cooldowns[PLAYER_ID] = BUILD_COOLDOWN
            self.status = f"도시 레벨 {city.level}"
            return
        kind = action.replace("build_", "")
        if kind == "sam":
            kind = "sam"
        if self.buildings_at(x, y):
            self.status = "건설 실패: 이미 건물이 있음"
            return
        faction.money -= cost
        self.buildings.append(Building(kind, PLAYER_ID, x, y))
        self.build_cooldowns[PLAYER_ID] = BUILD_COOLDOWN
        if kind in {"factory", "supply"}:
            self.mark_supply_dirty()
        self.status = "건설 완료"

    def buy_aircraft(self, kind: str) -> None:
        faction = self.factions[PLAYER_ID]
        if not any(b.owner == PLAYER_ID and b.kind == "airbase" for b in self.buildings):
            self.status = "구매 실패: 공군기지가 필요함"
            return
        cost = 95 if kind == "fighter" else 140
        if faction.money < cost:
            self.status = "구매 실패: 돈 부족"
            return
        faction.money -= cost
        if kind == "fighter":
            faction.fighters += 1
            self.status = "전투기 구매"
        else:
            faction.bombers += 1
            self.status = "폭격기 구매"

    def buy_ship(self) -> None:
        faction = self.factions[PLAYER_ID]
        if faction.money < 160:
            self.status = "구매 실패: 돈 부족"
            return
        if not any(b.owner == PLAYER_ID and b.kind == "port" for b in self.buildings):
            self.status = "전투함 구매 실패: 항구가 필요함"
            return
        faction.money -= 160
        faction.ships += 1
        self.status = "전투함 구매"

    def closest_owned_coast(self, x: int, y: int) -> tuple[int, int] | None:
        owned = [(cx, cy) for cx in range(self.width) for cy in range(self.height) if self.owner[cx][cy] == PLAYER_ID and self.is_coast(cx, cy)]
        return min(owned, key=lambda p: abs(p[0] - x) + abs(p[1] - y), default=None)

    def closest_launch_coast_from_owned_land(self, x: int, y: int) -> tuple[int, int] | None:
        owned = [(cx, cy) for cx in range(self.width) for cy in range(self.height) if self.owner[cx][cy] == PLAYER_ID]
        coasts = [(cx, cy) for cx in range(self.width) for cy in range(self.height) if self.land[cx][cy] and self.is_coast(cx, cy)]
        if not owned or not coasts:
            return None
        nearest_owned = min(owned, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
        return min(coasts, key=lambda p: abs(p[0] - nearest_owned[0]) + abs(p[1] - nearest_owned[1]))

    def closest_coast(self, x: int, y: int) -> tuple[int, int] | None:
        cells = [(cx, cy) for cx in range(self.width) for cy in range(self.height) if self.land[cx][cy] and self.is_coast(cx, cy)]
        return min(cells, key=lambda p: abs(p[0] - x) + abs(p[1] - y), default=None)

    def closest_water(self, x: int, y: int) -> tuple[int, int] | None:
        cells = [(cx, cy) for cx in range(self.width) for cy in range(self.height) if not self.land[cx][cy]]
        return min(cells, key=lambda p: abs(p[0] - x) + abs(p[1] - y), default=None)

    def adjacent_water(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            (x + dx, y + dy)
            for dx, dy in NEIGHBORS
            if 0 <= x + dx < self.width and 0 <= y + dy < self.height and not self.land[x + dx][y + dy]
        ]

    def water_path_between_coasts(self, start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int]] | None:
        starts = self.adjacent_water(*start)
        goals = set(self.adjacent_water(*target))
        if not starts or not goals:
            return None
        queue = deque(starts)
        previous: dict[tuple[int, int], tuple[int, int] | None] = {cell: None for cell in starts}
        goal: tuple[int, int] | None = None
        while queue:
            cell = queue.popleft()
            if cell in goals:
                goal = cell
                break
            x, y = cell
            for dx, dy in NEIGHBORS:
                nx, ny = x + dx, y + dy
                nxt = (nx, ny)
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if self.land[nx][ny] or nxt in previous:
                    continue
                previous[nxt] = cell
                queue.append(nxt)
        if goal is None:
            return None
        path: list[tuple[int, int]] = []
        current: tuple[int, int] | None = goal
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        return path

    def compress_water_path(self, path: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if len(path) <= 2:
            return path
        compressed = [path[0]]
        anchor_index = 0
        probe_index = 2
        while probe_index < len(path):
            if not self.clear_water_line(path[anchor_index], path[probe_index]):
                compressed.append(path[probe_index - 1])
                anchor_index = probe_index - 1
            probe_index += 1
        compressed.append(path[-1])
        return compressed

    def clear_water_line(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        x0, y0 = start
        x1, y1 = end
        steps = max(abs(x1 - x0), abs(y1 - y0))
        if steps == 0:
            return not self.land[x0][y0]
        for i in range(steps + 1):
            t = i / steps
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            if not (0 <= x < self.width and 0 <= y < self.height) or self.land[x][y]:
                return False
        return True

    def is_coast(self, x: int, y: int) -> bool:
        if not self.land[x][y]:
            return False
        for dx, dy in NEIGHBORS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height and not self.land[nx][ny]:
                return True
        return False

    def buildings_at(self, x: int, y: int) -> list[Building]:
        return [b for b in self.buildings if b.x == x and b.y == y]

    def transfer_buildings_at(self, x: int, y: int, owner: int) -> None:
        changed_supply = False
        for building in self.buildings:
            if building.x == x and building.y == y:
                building.owner = owner
                building.timer = 0
                if building.kind in {"factory", "supply"}:
                    changed_supply = True
        if changed_supply:
            self.mark_supply_dirty()

    def destroy_buildings_at(self, x: int, y: int) -> None:
        changed_supply = any(b.x == x and b.y == y and b.kind in {"factory", "supply"} for b in self.buildings)
        self.buildings = [b for b in self.buildings if not (b.x == x and b.y == y)]
        if changed_supply:
            self.mark_supply_dirty()

    def update_alive(self) -> None:
        for fid, count in enumerate(self.territory_counts):
            was_alive = self.factions[fid].alive
            self.factions[fid].alive = count > 0
            if was_alive and count <= 0:
                self.add_world_log(f"{self.factions[fid].name} 멸망")
            self.clamp_faction_troops(fid)
        self.wars = {
            war
            for war in self.wars
            if all(self.factions[fid].alive for fid in war)
        }

    def capturable_territory_counts(self) -> tuple[int, list[int]]:
        counts = [0 for _ in self.factions]
        total = 0
        for x in range(self.width):
            for y in range(self.height):
                if not self.land[x][y] or (x, y) in self.fallout:
                    continue
                total += 1
                owner = self.owner[x][y]
                if owner is not None:
                    counts[owner] += 1
        return total, counts

    def update_game_end(self, dt: float) -> None:
        if self.territory_counts[PLAYER_ID] <= 0:
            self.finish_game("defeat")
            return
        self.game_end_check_timer += dt
        if self.game_end_check_timer < GAME_END_CHECK_INTERVAL:
            return
        elapsed = self.game_end_check_timer
        self.game_end_check_timer = 0.0
        capturable_total, capturable_counts = self.capturable_territory_counts()
        if capturable_total <= 0:
            self.victory_timer = 0.0
            return
        player_ratio = capturable_counts[PLAYER_ID] / capturable_total
        enemies_crushed = all(capturable_counts[fid] <= ENEMY_SURVIVOR_PIXEL_LIMIT for fid in range(1, len(self.factions)))
        if player_ratio >= VICTORY_CONTROL_RATIO and enemies_crushed:
            self.victory_timer += elapsed
            remaining = max(0, VICTORY_HOLD_TIME - self.victory_timer)
            if remaining > 0:
                self.status = f"승리 조건 유지 중: {remaining:.0f}초"
            else:
                self.finish_game("victory")
        else:
            self.victory_timer = 0.0

    def finish_game(self, result: str) -> None:
        self.game_over = True
        self.game_result = result
        self.operations.clear()
        self.units = [unit for unit in self.units if unit.kind == "ship"]
        self.menu = None
        if result == "victory":
            self.status = "승리: PixelWars 종료"
        else:
            self.status = "패배: 보유 픽셀이 모두 사라짐"

    def troop_capacity(self, fid: int) -> int:
        return max(0, self.territory_counts[fid] * TROOPS_PER_PIXEL_CAP)

    def clamp_faction_troops(self, fid: int) -> None:
        self.factions[fid].troops = min(self.factions[fid].troops, self.troop_capacity(fid))

    def update_slider(self, mouse_x: int) -> None:
        rect = self.slider_rect()
        self.operation_percent = max(0, min(1, (mouse_x - rect.x) / rect.w))

    def slider_rect(self) -> pygame.Rect:
        panel = self.panel_rect()
        return pygame.Rect(panel.x + 28, self.panel_controls_y() - self.panel_scroll, panel.w - 56, 18)

    def panel_controls_y(self) -> int:
        return 64 + len(self.panel_lines()) * 24 + 8

    def panel_lines(self) -> list[str]:
        player = self.factions[PLAYER_ID]
        return [
            f"버전: {GAME_VERSION}",
            f"맵: {self.map_files[self.map_index].name} (1/2 이동, R 랜덤)",
            f"돈: {player.money}   병력: {player.troops}/{self.troop_capacity(PLAYER_ID)}",
            f"전투기: {player.fighters}  폭격기: {player.bombers}",
            f"전투함: {player.ships}",
            f"건설 쿨타임: {self.build_cooldowns.get(PLAYER_ID, 0.0):.1f}초",
            f"미사일 쿨: {player.ballistic_cooldown:.0f}s / 핵 {player.nuke_cooldown:.0f}s",
            f"승리 유지: {min(VICTORY_HOLD_TIME, self.victory_timer):.0f}/{VICTORY_HOLD_TIME:.0f}초",
            f"게임 속도: {'온라인 고정' if self.multiplayer_speed_locked() else f'{self.sim_speed:g}x'}",
            f"확대: {self.scale / self.base_scale:.1f}x",
            f"표시: 건물 {'ON' if self.building_visible_at_current_zoom() else 'OFF'} / 영토이미지 {'ON' if self.territory_images_enabled else 'OFF'}",
            "",
            "H/F1/?: 도움말",
            "Tab: 사이드바 접기/펼치기",
            "F5/F9: .pxw 저장/불러오기 선택",
            "C: AI성향  V: 보급  E: 작전",
            "G: 건물 표시   T: 영토 이미지",
            "WASD: 이동   휠: 확대/축소",
            "ESC: 일시정지   L: 로비   -/=: 속도",
            "좌클릭: 수도 선택/작전 생성",
            "우클릭: 작전/건설 메뉴",
            "F/B/N: 전투기/폭격기/전투함 구매",
            "",
            "좌클릭 작전 투입 병력",
        ]

    def scroll_panel(self, wheel_y: int) -> None:
        max_scroll = max(0, self.panel_content_height - SCREEN_H + 72)
        self.panel_scroll = max(0, min(max_scroll, self.panel_scroll - wheel_y * 38))

    def max_operation_troops(self) -> int:
        return max(0, self.factions[PLAYER_ID].troops)

    def selected_operation_troops(self) -> int:
        return int(self.max_operation_troops() * self.operation_percent)

    def operation_percent_text(self) -> str:
        return f"{int(round(self.operation_percent * 100))}%"

    def target_name(self, target: int | None) -> str:
        return "빈땅(None)" if target is None else self.factions[target].name

    def active_player_operations(self) -> list[Operation]:
        return [op for op in self.operations if op.owner == PLAYER_ID]

    def war_lines(self) -> list[str]:
        lines = []
        for war in sorted(self.wars, key=lambda item: sorted(item)):
            a, b = sorted(war)
            lines.append(f"{self.factions[a].name} vs {self.factions[b].name}")
        return lines

    def player_supply_coverage_estimate(self) -> int:
        owned = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if self.owner[x][y] == PLAYER_ID
        ]
        if not owned:
            return 0
        if len(owned) <= 300:
            sample = owned
        else:
            step = max(1, len(owned) // 300)
            sample = owned[::step][:300]
        covered = sum(1 for x, y in sample if self.in_supply_range(PLAYER_ID, x, y))
        return int(round(covered / len(sample) * 100))

    def player_threat_lines(self) -> list[str]:
        neighbors = [owner for owner in self.neighbor_owners(PLAYER_ID) if owner not in {None, PLAYER_ID}]
        if not neighbors:
            return ["인접 위협: 없음"]
        rows = []
        player_troops = max(1, self.factions[PLAYER_ID].troops)
        for fid in neighbors:
            ratio = self.factions[fid].troops / player_troops
            pressure = "높음" if ratio >= 1.25 else "보통" if ratio >= 0.75 else "낮음"
            rows.append((ratio, f"{self.factions[fid].name} 위협 {pressure}"))
        rows.sort(reverse=True)
        return [line for _ratio, line in rows[:3]]

    def save_game(self, autosave: bool = False) -> None:
        SAVE_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "autosave" if autosave else "pixelwars"
        path = SAVE_DIR / f"{prefix}_{stamp}.pxw"
        data = {
            "version": 1,
            "map": self.map_files[self.map_index].name,
            "map_size_key": self.map_size_key,
            "ai_count": self.ai_count,
            "pace_key": self.pace_key,
            "choosing_capital": self.choosing_capital,
            "operation_percent": self.operation_percent,
            "camera": [self.camera_x, self.camera_y, self.scale],
            "owner": [[-1 if self.owner[x][y] is None else self.owner[x][y] for y in range(self.height)] for x in range(self.width)],
            "factions": [f.__dict__ for f in self.factions],
            "buildings": [b.__dict__ for b in self.buildings],
            "units": [
                {
                    **u.__dict__,
                    "source": list(u.source) if u.source else None,
                    "target_cell": list(u.target_cell) if u.target_cell else None,
                    "path": [list(p) for p in u.path],
                }
                for u in self.units
            ],
            "operations": [
                {
                    **op.__dict__,
                    "cells": [list(c) for c in op.cells] if op.cells is not None else None,
                    "focus": list(op.focus) if op.focus else None,
                }
                for op in self.operations
            ],
            "wars": [list(war) for war in self.wars],
            "fallout": [[x, y, remaining] for (x, y), remaining in self.fallout.items()],
            "fallout_timer": self.fallout_timer,
            "build_cooldowns": {str(owner): remaining for owner, remaining in self.build_cooldowns.items()},
            "game_over": self.game_over,
            "game_result": self.game_result,
            "victory_timer": self.victory_timer,
            "screen_mode": self.screen_mode,
            "autosave_timer": self.autosave_timer,
            "paused": self.paused,
            "sim_speed": self.sim_speed,
            "show_buildings": self.show_buildings,
            "show_owner_borders": self.show_owner_borders,
            "show_support_zones": self.show_support_zones,
            "show_ai_traits": self.show_ai_traits,
            "show_operation_info": self.show_operation_info,
            "territory_images_enabled": self.territory_images_enabled,
            "territory_image_file": self.territory_image_file,
            "territory_image_mode": self.territory_image_mode,
            "world_log": self.world_log[:WORLD_LOG_LIMIT],
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if autosave:
            self.prune_autosaves()
        self.status = f"{'자동저장' if autosave else '저장'} 완료: {path.name}"

    def prune_autosaves(self) -> None:
        autosaves = sorted(SAVE_DIR.glob("autosave_*.pxw"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_save in autosaves[AUTOSAVE_KEEP:]:
            try:
                old_save.unlink()
            except OSError:
                pass

    def load_latest_save(self) -> None:
        saves = sorted(SAVE_DIR.glob("*.pxw"), key=lambda p: p.stat().st_mtime)
        if not saves:
            self.status = "불러오기 실패: .pxw 저장 파일 없음"
            return
        self.load_game(saves[-1])

    def open_save_picker(self) -> None:
        SAVE_DIR.mkdir(exist_ok=True)
        self.save_picker_items = sorted(SAVE_DIR.glob("*.pxw"), key=lambda p: p.stat().st_mtime, reverse=True)
        self.save_picker_meta = {path: self.save_summary(path) for path in self.save_picker_items}
        self.save_picker_scroll = 0
        self.show_save_picker = True
        if not self.save_picker_items:
            self.status = "불러오기 실패: .pxw 저장 파일 없음"

    def scroll_save_picker(self, wheel_y: int) -> None:
        max_scroll = max(0, len(self.save_picker_items) * 48 - 420)
        self.save_picker_scroll = max(0, min(max_scroll, self.save_picker_scroll - wheel_y * 38))

    def click_save_picker(self, mx: int, my: int) -> None:
        rect = self.save_picker_rect()
        if not rect.collidepoint(mx, my):
            self.show_save_picker = False
            return
        close_rect = pygame.Rect(rect.right - 86, rect.y + 18, 58, 26)
        if close_rect.collidepoint(mx, my):
            self.show_save_picker = False
            return
        list_top = rect.y + 72
        index = int((my - list_top + self.save_picker_scroll) // 48)
        if 0 <= index < len(self.save_picker_items):
            self.show_save_picker = False
            self.load_game(self.save_picker_items[index])

    def save_picker_rect(self) -> pygame.Rect:
        return pygame.Rect(260, 110, SCREEN_W - 520, SCREEN_H - 220)

    def save_summary(self, path: Path) -> str:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            factions = data.get("factions", [])
            player = factions[PLAYER_ID] if factions else {}
            return (
                f"{data.get('map', '?')} · AI {data.get('ai_count', max(0, len(factions) - 1))} · "
                f"{data.get('map_size_key', 'normal')} · {data.get('pace_key', 'standard')} · "
                f"병력 {player.get('troops', '?')}"
            )
        except (OSError, json.JSONDecodeError, TypeError, IndexError):
            return "세이브 정보를 읽을 수 없음"

    def load_game(self, path: Path) -> None:
        try:
            self._load_game(path)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError) as exc:
            self.status = f"불러오기 실패: 깨진 세이브 또는 호환되지 않는 파일 ({path.name})"
            self.add_world_log(f"세이브 로드 실패: {path.name}")
            print(f"Save load failed: {path} ({exc})")

    def _load_game(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("owner"), list) or not data.get("owner"):
            raise ValueError("owner grid missing")
        if not isinstance(data.get("factions"), list) or not data.get("factions"):
            raise ValueError("factions missing")
        self.map_size_key = data.get("map_size_key", self.map_size_key)
        self.ai_count = data.get("ai_count", self.ai_count)
        if self.ai_count not in AI_COUNT_OPTIONS:
            self.ai_count = min(AI_COUNT_OPTIONS, key=lambda value: abs(value - self.ai_count))
        self.pace_key = data.get("pace_key", self.pace_key)
        if self.pace_key not in {str(option["key"]) for option in PACE_OPTIONS}:
            self.pace_key = "standard"
        map_name = data.get("map")
        matches = [i for i, p in enumerate(self.discover_maps()) if p.name == map_name]
        self.load_map(matches[0] if matches else 0)
        if len(data["owner"]) != self.width or len(data["owner"][0]) != self.height:
            self.status = "불러오기 실패: 맵 크기가 다름"
            return
        self.choosing_capital = data.get("choosing_capital", False)
        self.operation_percent = data.get("operation_percent", 0.25)
        self.camera_x, self.camera_y, self.scale = data.get("camera", [self.camera_x, self.camera_y, self.scale])
        self.rebuild_map_surface()
        self.owner = [[None if data["owner"][x][y] < 0 else data["owner"][x][y] for y in range(self.height)] for x in range(self.width)]
        faction_data = []
        for f in data["factions"]:
            f.setdefault("unsupplied_time", 0.0)
            f.setdefault("unsupplied_start_troops", None)
            f.setdefault("ballistic_cooldown", 0.0)
            f.setdefault("nuke_cooldown", 0.0)
            faction_data.append(f)
        self.factions = [Faction(**f) for f in faction_data]
        self.ai_count = max(0, len(self.factions) - 1)
        self.buildings = [Building(**b) for b in data.get("buildings", [])]
        self.units = [
            Unit(
                **{
                    **u,
                    "source": tuple(u["source"]) if u.get("source") else None,
                    "target_cell": tuple(u["target_cell"]) if u.get("target_cell") else None,
                    "path": [tuple(p) for p in u.get("path", [])],
                }
            )
            for u in data.get("units", [])
        ]
        self.operations = [
            Operation(
                **{
                    **op,
                    "cells": {tuple(c) for c in op["cells"]} if op.get("cells") is not None else None,
                    "focus": tuple(op["focus"]) if op.get("focus") else None,
                    "pixel_cost": op.get("pixel_cost", PIXEL_ATTACK_COST),
                    "label": op.get("label", "작전"),
                    "timer": op.get("timer", 0.0),
                    "age": op.get("age", 0.0),
                    "supply_grace": op.get("supply_grace", 0.0),
                    "finished": op.get("finished", False),
                }
            )
            for op in data.get("operations", [])
        ]
        self.wars = {frozenset(war) for war in data.get("wars", [])}
        self.fallout = {(x, y): remaining for x, y, remaining in data.get("fallout", [])}
        self.fallout_timer = data.get("fallout_timer", 0.0)
        self.build_cooldowns = {int(owner): remaining for owner, remaining in data.get("build_cooldowns", {}).items()}
        self.game_over = data.get("game_over", False)
        self.game_result = data.get("game_result")
        self.victory_timer = data.get("victory_timer", 0.0)
        self.autosave_timer = data.get("autosave_timer", 0.0)
        self.paused = data.get("paused", False)
        self.sim_speed = data.get("sim_speed", 1.0)
        self.show_buildings = data.get("show_buildings", True)
        self.show_owner_borders = data.get("show_owner_borders", False)
        self.show_support_zones = data.get("show_support_zones", "off")
        if self.show_support_zones is False:
            self.show_support_zones = "off"
        elif self.show_support_zones is True:
            self.show_support_zones = "full"
        self.show_ai_traits = data.get("show_ai_traits", False)
        self.show_operation_info = data.get("show_operation_info", False)
        self.territory_images_enabled = data.get("territory_images_enabled", True)
        self.territory_image_file = data.get("territory_image_file")
        self.territory_image_mode = data.get("territory_image_mode", "tile")
        if self.territory_image_mode not in {key for key, _label in TERRITORY_IMAGE_MODES}:
            self.territory_image_mode = "tile"
        self.world_log = list(data.get("world_log", []))[:WORLD_LOG_LIMIT]
        self.screen_mode = "game"
        self.load_territory_images()
        self.rebuild_territory_counts()
        self.rebuild_owner_overlay()
        self.rebuild_frontiers()
        self.mark_supply_dirty()
        self.ensure_supply_networks()
        self.status = f"불러오기 완료: {path.name}"

    def draw(self) -> None:
        if self.screen_mode in {"lobby", "matching"}:
            self.draw_lobby_scene()
            if self.show_help:
                self.draw_help()
            if self.show_save_picker:
                self.draw_save_picker()
            pygame.display.flip()
            return
        self.screen.fill((18, 22, 30))
        self.screen.set_clip(self.map_view_rect)
        self.screen.blit(self.map_surface, (int(self.camera_x), int(self.camera_y)))
        self.draw_terrain_overlay()
        self.draw_ownership()
        self.draw_fallout()
        if self.show_support_zones != "off":
            self.draw_supply_ranges()
        if self.show_operation_info:
            self.draw_operation_arrows()
        if self.building_visible_at_current_zoom():
            self.draw_buildings()
        self.draw_units()
        self.screen.set_clip(None)
        pygame.draw.rect(self.screen, (25, 29, 38), self.panel_rect())
        self.draw_panel()
        if self.menu:
            self.draw_menu()
        if self.show_help:
            self.draw_help()
        if self.show_save_picker:
            self.draw_save_picker()
        if self.game_over:
            self.draw_game_over()
        if self.paused and not self.game_over:
            self.draw_pause_overlay()
        pygame.display.flip()

    def draw_lobby_scene(self) -> None:
        self.screen.fill((14, 18, 26))
        preview_rect = pygame.Rect(0, 0, SCREEN_W, SCREEN_H)
        preview_scale = max(SCREEN_W / self.map_surface.get_width(), SCREEN_H / self.map_surface.get_height())
        preview = pygame.transform.smoothscale(
            self.map_surface,
            (int(self.map_surface.get_width() * preview_scale), int(self.map_surface.get_height() * preview_scale)),
        )
        self.screen.blit(preview, preview.get_rect(center=preview_rect.center))
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((6, 10, 18, 190))
        self.screen.blit(shade, (0, 0))
        if self.screen_mode == "matching":
            self.draw_matching()
        else:
            self.draw_lobby()

    def draw_lobby(self) -> None:
        self.lobby_buttons = []
        title = self.big.render("PixelWars Lobby", True, (245, 249, 255))
        self.screen.blit(title, (82, 72))
        subtitle = self.font.render("맵 크기, 전쟁 규모, 전략 템포를 정하고 전쟁을 시작합니다.", True, (205, 216, 235))
        self.screen.blit(subtitle, (84, 112))

        info_rect = pygame.Rect(80, 170, 520, 320)
        pygame.draw.rect(self.screen, (28, 34, 46), info_rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 116, 150), info_rect, 1, border_radius=8)
        lines = [
            f"선택 맵: {self.map_files[self.map_index].name}",
            f"맵 크기: {self.map_size_label()} ({self.width}x{self.height})",
            f"전쟁 규모: {self.ai_count_label()} (AI {self.ai_count}명)",
            f"전략 템포: {self.pace_label()} - {self.pace_description()}",
            f"온라인: {self.online_status}",
            f"온라인 READY: {len(self.online_ready_players())}/{len(self.online_players())}" if self.online_lobby_active() else "온라인 전투: 로비/매칭만 지원, 전투 동기화 예정",
            f"승리 조건: 오염 제외 95% 점령 + 적 5픽셀 이하 2분 유지",
        ]
        y = info_rect.y + 34
        for line in lines:
            text = self.font.render(line, True, (226, 233, 245))
            self.screen.blit(text, (info_rect.x + 28, y))
            y += 38

        self.draw_lobby_button("match", "매칭 시작", 80, 530, 220, 48, (76, 138, 255))
        self.draw_lobby_button("prev_map", "이전 맵", 322, 530, 130, 48, (50, 60, 80))
        self.draw_lobby_button("next_map", "다음 맵", 466, 530, 130, 48, (50, 60, 80))
        self.draw_lobby_button("random_map", "랜덤 맵", 610, 530, 130, 48, (50, 60, 80))
        self.draw_lobby_button("map_size", f"크기: {self.map_size_label()}", 80, 594, 132, 42, (54, 70, 96))
        self.draw_lobby_button("ai_count", f"{self.ai_count_label()}: {self.ai_count}", 224, 594, 210, 42, (54, 70, 96))
        self.draw_lobby_button("pace", f"템포: {self.pace_label()}", 446, 594, 132, 42, (54, 70, 96))
        self.draw_lobby_button("load_save", "저장 불러오기", 590, 594, 150, 42, (54, 70, 96))
        self.draw_lobby_button("host_online", "온라인 방 만들기", 322, 646, 160, 36, (54, 70, 96))
        self.draw_lobby_button("join_local", "로컬 참가", 496, 646, 120, 36, (54, 70, 96))
        self.draw_lobby_button("disconnect_online", "연결 해제", 630, 646, 110, 36, (54, 70, 96))

        online_players = self.online_players()
        ready_players = set(self.online_ready_players())
        roster_rect = pygame.Rect(790, 170, 360, 320)
        pygame.draw.rect(self.screen, (28, 34, 46), roster_rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 116, 150), roster_rect, 1, border_radius=8)
        title = self.font.render("온라인 로비", True, (246, 249, 255))
        self.screen.blit(title, (roster_rect.x + 24, roster_rect.y + 28))
        code = self.small.render(f"방 주소: {self.online_host_hint}:{DEFAULT_PORT}", True, (165, 176, 196))
        self.screen.blit(code, (roster_rect.x + 24, roster_rect.y + 58))
        input_rect = pygame.Rect(roster_rect.x + 24, roster_rect.y + 252, 210, 30)
        pygame.draw.rect(self.screen, (18, 23, 34), input_rect, border_radius=4)
        pygame.draw.rect(self.screen, (110, 170, 255) if self.join_host_active else (85, 98, 126), input_rect, 1, border_radius=4)
        input_label = self.small.render(self.join_host_text + ("|" if self.join_host_active else ""), True, (226, 233, 245))
        self.screen.blit(input_label, (input_rect.x + 8, input_rect.y + 7))
        self.lobby_buttons.append(("host_input", input_rect))
        self.draw_lobby_button("join_host", "IP 참가", roster_rect.x + 244, roster_rect.y + 252, 86, 30, (54, 70, 96))
        ready_label = "준비 취소" if self.online_ready else "준비"
        ready_color = (62, 145, 92) if not self.online_ready else (120, 84, 54)
        self.draw_lobby_button("toggle_ready", ready_label, roster_rect.x + 24, roster_rect.y + 288, 110, 28, ready_color)
        if not online_players:
            empty = self.small.render("온라인 참가자 없음", True, (154, 164, 184))
            self.screen.blit(empty, (roster_rect.x + 24, roster_rect.y + 100))
        for i, name in enumerate(online_players[:9]):
            mark = "READY" if name in ready_players else "WAIT"
            color = (130, 255, 170) if name in ready_players else (226, 233, 245)
            text = self.small.render(f"{i + 1}. {name}  [{mark}]", True, color)
            self.screen.blit(text, (roster_rect.x + 24, roster_rect.y + 100 + i * 24))

        hints = [
            "Enter/Space: 매칭 시작",
            "1/2: 맵 변경",
            "R: 랜덤 맵",
            "3: 맵 크기  4: 전쟁 규모  5: 전략 템포",
            "온라인 방 만들기: LAN 로비 서버 시작",
            "로컬 참가: 같은 PC 로비 접속",
            "H/F1/?: 도움말",
        ]
        for i, line in enumerate(hints):
            text = self.small.render(line, True, (165, 176, 196))
            self.screen.blit(text, (84, 700 + i * 20))

    def draw_lobby_button(self, action: str, label: str, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, (145, 164, 200), rect, 1, border_radius=6)
        text = self.font.render(label, True, (246, 249, 255))
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.lobby_buttons.append((action, rect))

    def draw_matching(self) -> None:
        rect = pygame.Rect(SCREEN_W // 2 - 300, SCREEN_H // 2 - 130, 600, 260)
        pygame.draw.rect(self.screen, (28, 34, 46), rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 116, 150), rect, 1, border_radius=8)
        title = self.big.render("매칭 중", True, (245, 249, 255))
        self.screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 52)))
        progress = min(1.0, self.match_timer / self.match_duration)
        bar = pygame.Rect(rect.x + 70, rect.y + 112, rect.w - 140, 22)
        pygame.draw.rect(self.screen, (53, 61, 78), bar, border_radius=8)
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * progress), bar.h)
        pygame.draw.rect(self.screen, (76, 138, 255), fill, border_radius=8)
        found = self.font.render(f"Player 1/1  ·  AI {self.match_found}/{self.ai_count}  ·  {self.pace_label()} 템포", True, (226, 233, 245))
        self.screen.blit(found, found.get_rect(center=(rect.centerx, rect.y + 158)))
        if self.online_lobby_active():
            ready_text = f"READY {len(self.online_ready_players())}/{len(self.online_players())} · 전투 동기화는 다음 단계"
            ready_label = self.small.render(ready_text, True, (255, 225, 155))
            self.screen.blit(ready_label, ready_label.get_rect(center=(rect.centerx, rect.y + 184)))
        hint = self.small.render("ESC: 매칭 취소", True, (255, 225, 155))
        self.screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.y + 202)))

    def draw_ownership(self) -> None:
        # If border-only mode enabled, draw frontier cells instead of full overlay
        if self.show_owner_borders:
            for fid, frontier in enumerate(self.frontiers):
                color = faction_color(fid)
                for x, y in frontier:
                    sx, sy = self.cell_to_screen(x + 0.5, y + 0.5)
                    if self.map_view_rect.collidepoint(sx, sy):
                        radius = max(1, int(self.scale * 0.35))
                        pygame.draw.circle(self.screen, color, (sx, sy), radius, 1)
            # still optionally draw territory images over borders
            if self.territory_images_enabled and self.territory_images:
                texture_overlay = pygame.transform.scale(self.territory_image_overlay, self.map_surface.get_size())
                self.screen.blit(texture_overlay, (int(self.camera_x), int(self.camera_y)))
            return

        overlay = pygame.transform.scale(self.owner_overlay, self.map_surface.get_size())
        self.screen.blit(overlay, (int(self.camera_x), int(self.camera_y)))
        if self.territory_images_enabled and self.territory_images:
            texture_overlay = pygame.transform.scale(self.territory_image_overlay, self.map_surface.get_size())
            self.screen.blit(texture_overlay, (int(self.camera_x), int(self.camera_y)))

    def draw_terrain_overlay(self) -> None:
        overlay = pygame.transform.scale(self.terrain_overlay, self.map_surface.get_size())
        self.screen.blit(overlay, (int(self.camera_x), int(self.camera_y)))

    def draw_buildings(self) -> None:
        icons = {"city": "C", "factory": "F", "supply": "R", "airbase": "A", "port": "P", "sam": "M"}
        for b in self.buildings:
            sx, sy = self.cell_to_screen(b.x + 0.5, b.y + 0.5)
            if not self.map_view_rect.collidepoint(sx, sy):
                continue
            radius = max(5, int(self.scale * 0.9))
            pygame.draw.circle(self.screen, (8, 8, 10), (sx, sy), radius)
            text = self.small.render(icons.get(b.kind, "?"), True, (255, 255, 255))
            self.screen.blit(text, text.get_rect(center=(sx, sy)))

    def draw_supply_ranges(self) -> None:
        if self.show_support_zones == "off":
            return
        self.ensure_supply_networks()
        sources = self.active_supply_sources.get(PLAYER_ID, [])
        ranges = self.active_supply_ranges.get(PLAYER_ID, {})
        link_color = (80, 235, 120)
        if self.show_support_zones == "full":
            for start, end in self.active_supply_links.get(PLAYER_ID, []):
                sx, sy = self.cell_to_screen(start[0] + 0.5, start[1] + 0.5)
                ex, ey = self.cell_to_screen(end[0] + 0.5, end[1] + 0.5)
                if self.map_view_rect.clipline((sx, sy), (ex, ey)):
                    pygame.draw.line(self.screen, link_color, (sx, sy), (ex, ey), 2)
            for sx_cell, sy_cell in sources:
                radius = max(2, int(ranges.get((sx_cell, sy_cell), SUPPLY_RANGE) * self.scale))
                sx, sy = self.cell_to_screen(sx_cell + 0.5, sy_cell + 0.5)
                if not self.map_view_rect.inflate(radius * 2, radius * 2).collidepoint(sx, sy):
                    continue
                pygame.draw.circle(self.screen, link_color, (sx, sy), radius, 1)
        elif self.show_support_zones == "outline":
            current_hash = hash(
                tuple(
                    sorted(
                        (b.kind, b.x, b.y)
                        for b in self.buildings
                        if b.owner == PLAYER_ID and b.kind in {"factory", "supply"}
                    )
                )
            )
            if current_hash != self.last_supply_buildings_hash:
                self.last_supply_buildings_hash = current_hash
                supply_cells = set()
                for sx_cell, sy_cell in sources:
                    supply_range = ranges.get((sx_cell, sy_cell), SUPPLY_RANGE)
                    for x in range(max(0, sx_cell - supply_range), min(self.width, sx_cell + supply_range + 1)):
                        for y in range(max(0, sy_cell - supply_range), min(self.height, sy_cell + supply_range + 1)):
                            if (sx_cell - x) * (sx_cell - x) + (sy_cell - y) * (sy_cell - y) <= supply_range * supply_range:
                                supply_cells.add((x, y))
                self.outline_boundary_cells.clear()
                for x, y in supply_cells:
                    is_boundary = False
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < self.width and 0 <= ny < self.height) or (nx, ny) not in supply_cells:
                            is_boundary = True
                            break
                    if is_boundary:
                        self.outline_boundary_cells.add((x, y))
            for x, y in self.outline_boundary_cells:
                sx, sy = self.cell_to_screen(x + 0.5, y + 0.5)
                if self.map_view_rect.collidepoint(sx, sy):
                    pygame.draw.circle(self.screen, link_color, (sx, sy), max(1, int(self.scale * 0.35)), 1)

    def draw_operation_arrows(self) -> None:
        visible = 0
        for operation in self.operations:
            if operation.finished or operation.troops <= 0:
                continue
            path = self.operation_arrow_path(operation)
            if not path:
                continue
            screen_path = [self.cell_to_screen(x + 0.5, y + 0.5) for x, y in path]
            if not any(self.map_view_rect.inflate(80, 80).collidepoint(point) for point in screen_path):
                continue
            if operation.owner == PLAYER_ID:
                color = (90, 185, 255)
                width = 4
            else:
                color = (255, 120, 95)
                width = 2
            self.draw_path_arrow(screen_path, color, width)
            visible += 1
            if visible >= 32:
                break

    def operation_arrow_path(self, operation: Operation) -> list[tuple[int, int]] | None:
        candidates = self.operation_candidates(operation)
        if not candidates:
            return None
        support = self.operation_support_cells(operation, candidates)
        if not support:
            return None
        if operation.focus is not None:
            fx, fy = operation.focus
            support_center_x = sum(x for x, _y in support) / len(support)
            support_center_y = sum(y for _x, y in support) / len(support)
            dir_x, dir_y = fx - support_center_x, fy - support_center_y
            forward = [
                cell
                for cell in candidates
                if (cell[0] - support_center_x) * dir_x + (cell[1] - support_center_y) * dir_y >= -0.1
            ]
            if forward:
                candidates = forward
            candidates.sort(key=lambda cell: (abs(cell[0] - fx) + abs(cell[1] - fy), self.attack_score(cell, operation)))
        else:
            candidates.sort(key=lambda cell: self.attack_score(cell, operation))
        for target in candidates[: min(10, len(candidates))]:
            start = min(support, key=lambda cell: abs(cell[0] - target[0]) + abs(cell[1] - target[1]))
            path = self.land_arrow_path(start, target, operation.owner)
            if path:
                path = self.extend_arrow_tail(path, operation.owner)
                return self.simplify_arrow_path(path)
        return None

    def operation_support_cells(self, operation: Operation, candidates: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if operation.cells:
            return list(operation.cells)[: min(40, len(operation.cells))]
        support: list[tuple[int, int]] = []
        for x, y in candidates[: min(50, len(candidates))]:
            for dx, dy in NEIGHBORS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and self.owner[nx][ny] == operation.owner:
                    support.append((nx, ny))
                    break
        return support

    def land_arrow_path(self, start: tuple[int, int], target: tuple[int, int], owner: int) -> list[tuple[int, int]] | None:
        if start == target:
            return [start, target]
        queue = deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue and len(came_from) < 1600:
            x, y = queue.popleft()
            for dx, dy in NEIGHBORS:
                nxt = (x + dx, y + dy)
                nx, ny = nxt
                if not (0 <= nx < self.width and 0 <= ny < self.height) or nxt in came_from:
                    continue
                if not self.land[nx][ny]:
                    continue
                if nxt != target and self.owner[nx][ny] != owner:
                    continue
                came_from[nxt] = (x, y)
                if nxt == target:
                    path = [nxt]
                    cur = (x, y)
                    while cur is not None:
                        path.append(cur)
                        cur = came_from[cur]
                    path.reverse()
                    return path
                queue.append(nxt)
        if abs(start[0] - target[0]) + abs(start[1] - target[1]) == 1:
            return [start, target]
        return None

    def simplify_arrow_path(self, path: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if len(path) <= 3:
            return path
        simplified = [path[0]]
        last_dir = (path[1][0] - path[0][0], path[1][1] - path[0][1])
        for i in range(1, len(path) - 1):
            direction = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            if direction != last_dir:
                simplified.append(path[i])
                last_dir = direction
        simplified.append(path[-1])
        return simplified

    def extend_arrow_tail(self, path: list[tuple[int, int]], owner: int) -> list[tuple[int, int]]:
        if len(path) < 2:
            return path
        tail = [path[0]]
        target = path[-1]
        current = path[0]
        blocked = set(path)
        for _ in range(8):
            options: list[tuple[int, int]] = []
            for dx, dy in NEIGHBORS:
                nxt = (current[0] + dx, current[1] + dy)
                nx, ny = nxt
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and nxt not in blocked
                    and self.land[nx][ny]
                    and self.owner[nx][ny] == owner
                ):
                    options.append(nxt)
            if not options:
                break
            current = max(options, key=lambda cell: abs(cell[0] - target[0]) + abs(cell[1] - target[1]))
            tail.append(current)
            blocked.add(current)
        tail.reverse()
        return tail[:-1] + path

    def draw_path_arrow(self, points: list[tuple[int, int]], color: tuple[int, int, int], width: int) -> None:
        if len(points) < 2:
            return
        shadow_width = width + 5
        pygame.draw.lines(self.screen, (10, 12, 18), False, points, shadow_width)
        pygame.draw.lines(self.screen, color, False, points, width)
        for point in points[:-1]:
            pygame.draw.circle(self.screen, (10, 12, 18), point, max(2, shadow_width // 2))
            pygame.draw.circle(self.screen, color, point, max(1, width // 2))
        tip = points[-1]
        prev = points[-2]
        tangent_x, tangent_y = tip[0] - prev[0], tip[1] - prev[1]
        tangent_dist = max(1, math.hypot(tangent_x, tangent_y))
        ux, uy = tangent_x / tangent_dist, tangent_y / tangent_dist
        total_length = sum(math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(1, len(points)))
        head_len = int(min(max(8, width * 5), max(6, total_length * 0.38)))
        head_w = int(min(max(6, width * 3), max(4, total_length * 0.22)))
        left = (
            int(tip[0] - ux * head_len - uy * head_w),
            int(tip[1] - uy * head_len + ux * head_w),
        )
        right = (
            int(tip[0] - ux * head_len + uy * head_w),
            int(tip[1] - uy * head_len - ux * head_w),
        )
        pygame.draw.polygon(self.screen, (10, 12, 18), [tip, left, right])
        inner_left = (
            int(tip[0] - ux * (head_len - 2) - uy * (head_w - 2)),
            int(tip[1] - uy * (head_len - 2) + ux * (head_w - 2)),
        )
        inner_right = (
            int(tip[0] - ux * (head_len - 2) + uy * (head_w - 2)),
            int(tip[1] - uy * (head_len - 2) - ux * (head_w - 2)),
        )
        pygame.draw.polygon(self.screen, color, [tip, inner_left, inner_right])

    def draw_fallout(self) -> None:
        if not self.fallout:
            return
        start_x, end_x, start_y, end_y = self.visible_cell_bounds()
        size = max(1, int(self.scale + 0.8))
        color = (255, 70, 86, 92)
        layer = pygame.Surface(self.map_view_rect.size, pygame.SRCALPHA)
        for (x, y), _ in self.fallout.items():
            if start_x <= x < end_x and start_y <= y < end_y:
                sx, sy = self.cell_to_screen(x, y)
                pygame.draw.rect(layer, color, (sx - self.map_view_rect.x, sy - self.map_view_rect.y, size, size))
        self.screen.blit(layer, self.map_view_rect.topleft)

    def draw_units(self) -> None:
        colors = {
            "landing": (245, 245, 230),
            "fighter": (130, 220, 255),
            "bomber": (255, 220, 100),
            "ballistic": (255, 105, 95),
            "nuke": (255, 60, 125),
            "ship": (170, 205, 225),
        }
        for u in self.units:
            sx, sy = self.cell_to_screen(u.x, u.y)
            pygame.draw.circle(self.screen, colors.get(u.kind, (255, 255, 255)), (sx, sy), 5)

    def draw_game_over(self) -> None:
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        self.screen.blit(shade, (0, 0))
        rect = pygame.Rect(SCREEN_W // 2 - 220, SCREEN_H // 2 - 82, 440, 164)
        pygame.draw.rect(self.screen, (30, 35, 48), rect, border_radius=8)
        pygame.draw.rect(self.screen, (124, 145, 180), rect, 2, border_radius=8)
        victory = self.game_result == "victory"
        title = "승리" if victory else "패배"
        detail = "점령 조건을 2분 동안 유지했습니다." if victory else "보유 픽셀이 모두 사라졌습니다."
        title_color = (130, 255, 170) if victory else (255, 130, 130)
        title_surface = self.big.render(title, True, title_color)
        detail_surface = self.font.render(detail, True, (235, 240, 250))
        hint_surface = self.small.render("F5로 결과 저장 가능", True, (255, 225, 155))
        self.screen.blit(title_surface, title_surface.get_rect(center=(rect.centerx, rect.y + 48)))
        self.screen.blit(detail_surface, detail_surface.get_rect(center=(rect.centerx, rect.y + 88)))
        self.screen.blit(hint_surface, hint_surface.get_rect(center=(rect.centerx, rect.y + 122)))

    def draw_pause_overlay(self) -> None:
        self.pause_buttons = []
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 135))
        self.screen.blit(shade, (0, 0))
        rect = pygame.Rect(SCREEN_W // 2 - 205, SCREEN_H // 2 - 280, 410, 560)
        pygame.draw.rect(self.screen, (30, 35, 48), rect, border_radius=8)
        pygame.draw.rect(self.screen, (124, 145, 180), rect, 2, border_radius=8)
        title_text = "설정" if self.pause_menu_page == "settings" else "일시정지"
        title = self.big.render(title_text, True, (246, 249, 255))
        self.screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 42)))
        if self.pause_menu_page == "settings":
            image_name = self.territory_image_file or "선택 없음"
            if len(image_name) > 24:
                image_name = image_name[:21] + "..."
            buttons = [
                ("back", "뒤로"),
                ("buildings", f"건물 표시: {'켜짐' if self.show_buildings else '꺼짐'}"),
                ("support_zones", f"보급 레이어: {self.support_zones_label()}"),
                ("borders", f"테두리만 표시: {'켜짐' if self.show_owner_borders else '꺼짐'}"),
                ("territory_images", f"영토 이미지: {'켜짐' if self.territory_images_enabled else '꺼짐'}"),
                ("image_prev", "이전 이미지"),
                ("image_next", f"다음 이미지: {image_name}"),
                ("image_mode", f"채우기 방식: {self.territory_image_mode_label()}"),
                ("image_upload", "이미지 업로드"),
            ]
        else:
            buttons = [
                ("resume", "계속하기"),
                ("settings", "설정"),
                ("save", "저장"),
                ("load", "불러오기"),
                ("lobby", "게임 나가기"),
                ("quit", "게임 종료"),
            ]
        y = rect.y + 82
        for action, label in buttons:
            button = pygame.Rect(rect.x + 44, y, rect.w - 88, 38)
            color = (72, 96, 138) if action in {"resume", "settings", "back"} else (52, 60, 78)
            if action == "quit":
                color = (96, 50, 58)
            pygame.draw.rect(self.screen, color, button, border_radius=6)
            pygame.draw.rect(self.screen, (145, 164, 200), button, 1, border_radius=6)
            text = self.font.render(label, True, (246, 249, 255))
            self.screen.blit(text, text.get_rect(center=button.center))
            self.pause_buttons.append((action, button))
            y += 46
        hint = self.small.render("ESC: 계속하기   G: 건물 표시   T: 영토 이미지", True, (255, 225, 155))
        self.screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.bottom - 24)))

    def visible_cell_bounds(self) -> tuple[int, int, int, int]:
        start_x = max(0, int((-self.camera_x) / self.scale) - 2)
        end_x = min(self.width, int((self.map_view_rect.w - self.camera_x) / self.scale) + 3)
        start_y = max(0, int((-self.camera_y) / self.scale) - 2)
        end_y = min(self.height, int((self.map_view_rect.h - self.camera_y) / self.scale) + 3)
        return start_x, end_x, start_y, end_y

    def draw_panel(self) -> None:
        panel = self.panel_rect()
        if self.sidebar_collapsed:
            pygame.draw.rect(self.screen, (34, 39, 52), panel)
            label = self.small.render("Tab", True, (244, 247, 255))
            self.screen.blit(label, label.get_rect(center=(panel.centerx, 24)))
            arrow = self.big.render("<", True, (113, 189, 255))
            self.screen.blit(arrow, arrow.get_rect(center=(panel.centerx, 58)))
            return
        self.screen.set_clip(panel)
        x = panel.x + 22
        offset = -self.panel_scroll
        player = self.factions[PLAYER_ID]
        title = self.big.render("PixelWars", True, (244, 247, 255))
        self.screen.blit(title, (x, 18 + offset))
        lines = self.panel_lines()
        y = 64 + offset
        for line in lines:
            text = self.font.render(line, True, (218, 225, 238))
            self.screen.blit(text, (x, y))
            y += 24
        rect = self.slider_rect()
        pygame.draw.rect(self.screen, (70, 78, 94), rect, border_radius=8)
        max_troops = self.max_operation_troops()
        selected_troops = self.selected_operation_troops()
        t = self.operation_percent
        knob_x = rect.x + int(rect.w * t)
        pygame.draw.circle(self.screen, (113, 189, 255), (knob_x, rect.centery), 10)
        value = self.font.render(f"{self.operation_percent_text()} ({selected_troops}/{max_troops})", True, (244, 247, 255))
        self.screen.blit(value, (rect.right + 8, rect.y - 4))
        after_minimap = self.draw_minimap(x, rect.bottom + 30)
        after_stats = self.draw_player_stats(x, after_minimap + 24)
        after_cursor = after_stats
        if self.show_operation_info:
            after_cursor = self.draw_operation_table(x, after_cursor + 24)
        else:
            self.operation_cancel_rects = []
        after_factions = self.draw_faction_table(x, after_cursor + 24)
        after_log = self.draw_world_log(x, after_factions + 24)
        self.panel_content_height = max(SCREEN_H, after_log - offset + 70)
        self.panel_scroll = min(self.panel_scroll, max(0, self.panel_content_height - SCREEN_H + 72))
        self.screen.set_clip(None)
        pygame.draw.rect(self.screen, (25, 29, 38), (panel.x, SCREEN_H - 56, panel.w, 56))
        status = self.small.render(self.status[:42], True, (255, 225, 155))
        self.screen.blit(status, (x, SCREEN_H - 42))
        hint = self.small.render("휠: 사이드바 스크롤", True, (154, 164, 184))
        self.screen.blit(hint, (x, SCREEN_H - 22))
        if self.choosing_capital:
            prompt = self.big.render("수도 위치를 좌클릭  ·  C 자동 배치", True, (255, 245, 190))
            shadow = self.big.render("수도 위치를 좌클릭  ·  C 자동 배치", True, (0, 0, 0))
            self.screen.blit(shadow, (28, 28))
            self.screen.blit(prompt, (26, 26))

    def draw_minimap(self, x: int, y: int) -> int:
        header = self.font.render("미니맵", True, (244, 247, 255))
        self.screen.blit(header, (x, y))
        y += 26
        width = self.panel_rect().w - 44
        height = max(70, int(width * self.height / max(1, self.width)))
        height = min(150, height)
        rect = pygame.Rect(x, y, width, height)
        self.minimap_rect = rect
        base = pygame.transform.scale(self.map_surface, rect.size)
        self.screen.blit(base, rect.topleft)
        overlay = pygame.transform.scale(self.owner_overlay, rect.size)
        self.screen.blit(overlay, rect.topleft)
        pygame.draw.rect(self.screen, (190, 206, 235), rect, 1)
        view_x = rect.x + int((-self.camera_x / max(1, self.width * self.scale)) * rect.w)
        view_y = rect.y + int((-self.camera_y / max(1, self.height * self.scale)) * rect.h)
        view_w = max(4, int(self.map_view_rect.w / max(1, self.width * self.scale) * rect.w))
        view_h = max(4, int(self.map_view_rect.h / max(1, self.height * self.scale) * rect.h))
        pygame.draw.rect(self.screen, (255, 245, 170), (view_x, view_y, view_w, view_h), 1)
        return rect.bottom

    def draw_player_stats(self, x: int, y: int) -> int:
        header = self.font.render("국가 통계", True, (244, 247, 255))
        self.screen.blit(header, (x, y))
        y += 26
        buildings = [b for b in self.buildings if b.owner == PLAYER_ID]
        counts = {kind: sum(1 for b in buildings if b.kind == kind) for kind in ["city", "factory", "supply", "airbase", "port", "sam"]}
        city_money = sum(8 * b.level for b in buildings if b.kind == "city")
        city_troops = sum(10 * b.level for b in buildings if b.kind == "city")
        port_money = counts["port"] * 14
        lines = [
            f"도시 {counts['city']}  공장 {counts['factory']}  보급로 {counts['supply']}",
            f"공군 {counts['airbase']}  항구 {counts['port']}  방공 {counts['sam']}",
            f"5초 생산: 돈 +{city_money + port_money}, 병력 +{city_troops}",
        ]
        if self.show_supply_info():
            lines.append(f"보급 추정: 영토 {self.player_supply_coverage_estimate()}%")
        if self.show_ai_traits:
            lines.extend(self.player_threat_lines())
        for line in lines:
            text = self.small.render(line, True, (214, 221, 233))
            self.screen.blit(text, (x, y))
            y += 20
        return y

    def draw_operation_table(self, x: int, y: int) -> int:
        self.operation_cancel_rects = []
        header = self.font.render("작전", True, (244, 247, 255))
        self.screen.blit(header, (x, y))
        y += 26
        operations = self.active_player_operations()
        if not operations:
            text = self.small.render("진행 중인 작전 없음", True, (154, 164, 184))
            self.screen.blit(text, (x, y))
            y += 22
        visible_rect = self.panel_rect().copy()
        visible_rect.h -= 56
        for index, operation in enumerate(operations):
            label = f"{index + 1}. {operation.label}: {self.target_name(operation.target)} / {operation.troops}명"
            if len(label) > 28:
                label = label[:27] + "…"
            text = self.small.render(label, True, (214, 221, 233))
            self.screen.blit(text, (x, y))
            button = pygame.Rect(x + 190, y - 2, 48, 22)
            pygame.draw.rect(self.screen, (86, 47, 55), button, border_radius=4)
            pygame.draw.rect(self.screen, (150, 75, 86), button, 1, border_radius=4)
            btn_text = self.small.render("취소", True, (255, 235, 238))
            self.screen.blit(btn_text, btn_text.get_rect(center=button.center))
            if visible_rect.colliderect(button):
                self.operation_cancel_rects.append((button, operation))
            y += 26
        y += 8
        war_header = self.font.render("전쟁 상태", True, (244, 247, 255))
        self.screen.blit(war_header, (x, y))
        y += 26
        wars = self.war_lines()
        if not wars:
            text = self.small.render("전쟁 없음", True, (154, 164, 184))
            self.screen.blit(text, (x, y))
            return y + 24
        for line in wars[:5]:
            text = self.small.render(line, True, (255, 178, 150))
            self.screen.blit(text, (x, y))
            y += 20
        return y

    def draw_faction_table(self, x: int, y: int) -> int:
        rows = []
        for fid, faction in enumerate(self.factions):
            rows.append((self.territory_counts[fid], fid, faction))
        rows.sort(reverse=True)
        header = self.font.render("세력 순위", True, (244, 247, 255))
        self.screen.blit(header, (x, y))
        y += 28
        for count, fid, faction in rows[:32]:
            pygame.draw.rect(self.screen, faction.color, (x, y + 4, 12, 12))
            trait = "" if fid == PLAYER_ID or not self.show_ai_traits else f" {AI_PERSONALITIES[faction.personality]['label']}"
            label = f"{faction.name}{trait}: {count}"
            text = self.small.render(label, True, (214, 221, 233))
            self.screen.blit(text, (x + 18, y))
            y += 20
        return y

    def show_supply_info(self) -> bool:
        return self.show_support_zones != "off"

    def draw_world_log(self, x: int, y: int) -> int:
        header = self.font.render("세계 로그", True, (244, 247, 255))
        self.screen.blit(header, (x, y))
        y += 26
        if not self.world_log:
            text = self.small.render("아직 주요 사건 없음", True, (154, 164, 184))
            self.screen.blit(text, (x, y))
            return y + 24
        for line in self.world_log[:WORLD_LOG_LIMIT]:
            if len(line) > 30:
                line = line[:29] + "..."
            text = self.small.render(line, True, (255, 214, 150))
            self.screen.blit(text, (x, y))
            y += 20
        return y

    def draw_menu(self) -> None:
        assert self.menu
        h = 34 + len(self.menu.options) * 30
        rect = pygame.Rect(self.menu.x, self.menu.y, 170, h)
        pygame.draw.rect(self.screen, (34, 39, 52), rect, border_radius=6)
        pygame.draw.rect(self.screen, (112, 126, 154), rect, 1, border_radius=6)
        title = self.small.render(self.menu.title, True, (255, 255, 255))
        self.screen.blit(title, (rect.x + 10, rect.y + 8))
        for i, (label, _) in enumerate(self.menu.options):
            item = pygame.Rect(rect.x + 5, rect.y + 28 + i * 30, 160, 27)
            pygame.draw.rect(self.screen, (50, 58, 76), item, border_radius=4)
            text = self.small.render(label, True, (235, 240, 250))
            self.screen.blit(text, (item.x + 8, item.y + 5))

    def draw_help(self) -> None:
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 145))
        self.screen.blit(shade, (0, 0))

        rect = pygame.Rect(150, 82, SCREEN_W - 300, SCREEN_H - 164)
        pygame.draw.rect(self.screen, (30, 35, 48), rect, border_radius=8)
        pygame.draw.rect(self.screen, (124, 145, 180), rect, 2, border_radius=8)

        title = self.big.render("PixelWars 도움말", True, (246, 249, 255))
        self.screen.blit(title, (rect.x + 28, rect.y + 24))
        close = self.small.render("H / F1 / ? / ESC 또는 클릭으로 닫기", True, (255, 225, 155))
        self.screen.blit(close, (rect.right - close.get_width() - 28, rect.y + 32))

        sections = [
            (
                "시작",
                [
                    "처음 화면은 로비이며 Enter/Space 또는 매칭 시작 버튼으로 시작합니다.",
                    "로비에서 맵 크기, 전쟁 규모, 전략 템포를 바꿀 수 있습니다.",
                    "전쟁 규모는 소규모/표준/대규모/세계 대전/혼돈입니다.",
                    "장기전 템포는 진격과 생산을 늦추고, 강한 AI 템포는 AI 자원과 행동성을 높입니다.",
                    "매칭 중 ESC를 누르면 로비로 돌아갑니다.",
                    "처음에는 육지를 좌클릭해서 플레이어 수도를 정합니다.",
                    "수도 주변은 시작 영토가 되고 도시와 공장만 생성됩니다.",
                    "영토 붕괴는 없고, 진격에는 보급망이 필요합니다.",
                    "보급망이 끊기면 3분 동안 병력이 최대 75%까지 약화됩니다.",
                    "맵은 시작 시 랜덤이며, 1/2로 이전/다음, R로 랜덤 변경할 수 있습니다.",
                ],
            ),
            (
                "카메라",
                [
                    "WASD로 이동합니다. Shift를 누르면 더 빠르게 이동합니다.",
                    "마우스 휠로 확대/축소합니다.",
                    "사이드바 위 휠은 사이드바 스크롤입니다.",
                    "Tab으로 사이드바를 접거나 펼칩니다.",
                    "F5로 .pxw 저장, F9로 저장 선택 창을 엽니다.",
                    "G로 건물 표시, T로 영토 이미지 표시를 켜고 끕니다.",
                    "C로 AI 성향, V로 보급, E로 작전 정보를 따로 표시합니다.",
                    "저장 선택 창은 맵, 전쟁 규모, 템포, 병력 요약을 함께 보여줍니다.",
                    "ESC로 일시정지 메뉴를 열고, L로 새 로비로 돌아갈 수 있습니다.",
                    "-와 = 키로 게임 속도를 0.5x~4x 사이에서 조절합니다. 온라인 참가자가 있으면 1x 고정입니다.",
                ],
            ),
            (
                "전쟁",
                [
                    "좌클릭하면 클릭한 땅의 주인과 슬라이더 병력이 하나의 작전으로 묶입니다.",
                    "슬라이더는 0%부터 100%까지이며 현재 보유 병력에 비례합니다.",
                    "주인이 없으면 빈땅(None) 개척 작전이 됩니다.",
                    "작전 병력은 픽셀 공격마다 줄고, 0이 되면 자동 파기됩니다.",
                    "진행 중인 작전은 가능한 육지 경로를 따라 화살표로 표시됩니다.",
                    "작전 화살표와 작전 목록은 E키로 켜고 끕니다.",
                    "적 영토 공격 소모량은 상대 예비 병력에 비례합니다.",
                    "상대 병력이 거의 없으면 병력 소모 없이 점령합니다.",
                    "병력 최대치는 점령 픽셀 수에 따라 제한됩니다.",
                    "None이 아닌 타겟을 공격하면 전쟁 상태에 등록됩니다.",
                    "병력으로 건물을 점령하면 파괴하지 않고 소유권을 가져옵니다.",
                    "오염 지역 제외 95% 이상 점령, 모든 적 5픽셀 이하를 2분 유지하면 승리합니다.",
                    "자신의 보유 픽셀이 0이 되면 패배합니다.",
                    "AI는 균형/공격/방어/경제/약탈/극공/극방 성향을 가집니다.",
                    "표준 AI는 같은 시작 자원으로 전선/보급 판단을 천천히 합니다.",
                    "C키를 누르면 세력 순위에 AI 성향과 인접 AI 위협도가 표시됩니다.",
                ],
            ),
            (
                "우클릭 작전",
                [
                    "상륙공격: 가장 가까운 아군 해안에서 배를 보내 해변 1칸을 점령합니다.",
                    "상륙/전투기 강습은 1분 동안 보급 밖에서도 유지됩니다.",
                    "공중공격: 전투기는 점령 후 귀환, 폭격기는 미사일 투하 후 귀환합니다.",
                    "탄도미사일은 공장/공군기지에서 발사되며 방공망 근처에서 65%로 요격됩니다.",
                    "핵탄도미사일은 반경 30칸을 비우고 10분 낙진 지역을 만듭니다.",
                    "전투함 배치: 바다에 두고 적 상륙선을 요격합니다.",
                    "자신의 땅을 우클릭하면 건설 메뉴가 열립니다.",
                ],
            ),
            (
                "건설과 구매",
                [
                    "공군기지: 전투기/폭격기 구매와 출격 조건입니다.",
                    "공장: 짧은 보급 중심입니다. 전선 확장에는 보급로가 더 효율적입니다.",
                    "보급로: 공장/활성 보급로와 연결 거리 안에 있으면 주변 36칸 진격을 허용합니다.",
                    "V키를 누르면 보급 연결선과 보급 범위를 지도에 표시합니다.",
                    "평원은 일반 지형이고, 산맥/사막은 진격 속도가 20% 느립니다.",
                    "확대 3x 이상에서는 건물 아이콘이 자동으로 숨겨집니다.",
                    "건물 건설과 도시 레벨업에는 5초 쿨타임이 있습니다.",
                    "일시정지 설정에서 영토 이미지를 업로드하고 타일/늘림/잘라 채우기를 고를 수 있습니다.",
                    "항구: 해변에만 건설 가능하며 돈을 벌고 전투함 구매 조건이 됩니다.",
                    "도시: 돈과 병력을 생산하며 최대 5레벨까지 올릴 수 있습니다.",
                    "방공미사일기지: 근처 항공기를 80% 확률로 격추합니다.",
                    "F 전투기 구매, B 폭격기 구매, N 전투함 구매",
                ],
            ),
        ]

        col_w = (rect.w - 72) // 2
        positions = [(rect.x + 28, rect.y + 78), (rect.x + 48 + col_w, rect.y + 78)]
        for idx, (heading, lines) in enumerate(sections):
            col = 0 if idx < 3 else 1
            x, y = positions[col]
            heading_text = self.font.render(heading, True, (128, 202, 255))
            self.screen.blit(heading_text, (x, y))
            y += 28
            for line in lines:
                body = self.small.render("• " + line, True, (226, 233, 245))
                self.screen.blit(body, (x, y))
                y += 22
            y += 18
            positions[col] = (x, y)

    def draw_save_picker(self) -> None:
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))

        rect = self.save_picker_rect()
        pygame.draw.rect(self.screen, (30, 35, 48), rect, border_radius=8)
        pygame.draw.rect(self.screen, (124, 145, 180), rect, 2, border_radius=8)
        title = self.big.render(".pxw 불러오기", True, (246, 249, 255))
        self.screen.blit(title, (rect.x + 28, rect.y + 22))
        close_rect = pygame.Rect(rect.right - 86, rect.y + 18, 58, 26)
        pygame.draw.rect(self.screen, (62, 72, 94), close_rect, border_radius=4)
        close = self.small.render("닫기", True, (244, 247, 255))
        self.screen.blit(close, close.get_rect(center=close_rect.center))

        hint = self.small.render("클릭해서 불러오기 / 휠로 스크롤 / ESC로 닫기", True, (255, 225, 155))
        self.screen.blit(hint, (rect.x + 28, rect.y + 52))

        list_rect = pygame.Rect(rect.x + 22, rect.y + 72, rect.w - 44, rect.h - 92)
        self.screen.set_clip(list_rect)
        if not self.save_picker_items:
            empty = self.font.render("저장 파일이 없습니다.", True, (214, 221, 233))
            self.screen.blit(empty, (list_rect.x + 8, list_rect.y + 12))
        for i, path in enumerate(self.save_picker_items):
            y = list_rect.y + i * 48 - self.save_picker_scroll
            if y < list_rect.y - 48 or y > list_rect.bottom:
                continue
            row = pygame.Rect(list_rect.x, y, list_rect.w, 44)
            pygame.draw.rect(self.screen, (45, 53, 70), row, border_radius=4)
            size_kb = max(1, path.stat().st_size // 1024)
            label = f"{path.name}  ({size_kb} KB)"
            text = self.small.render(label, True, (230, 236, 248))
            meta = self.small.render(self.save_picker_meta.get(path, ""), True, (165, 176, 196))
            self.screen.blit(text, (row.x + 10, row.y + 5))
            self.screen.blit(meta, (row.x + 10, row.y + 24))
        self.screen.set_clip(None)


def main() -> None:
    PixelWars().run()
