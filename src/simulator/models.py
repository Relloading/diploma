from enum import Enum
from pydantic import BaseModel
from typing import Dict


class DeviceType(str, Enum):
    LIGHT = "light"
    CURTAIN = "curtain"
    WINDOW = "window"
    AC = "ac"
    CLIMATE = "climate"
    TEMP_SENSOR = "temp_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"
    LIGHT_SENSOR = "light_sensor"
    MOTION_SENSOR = "motion_sensor"


class RoomType(str, Enum):
    BATHROOM = "bathroom"
    KITCHEN = "kitchen"
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"


class DeviceStatus(BaseModel):
    id: str
    type: DeviceType
    status: Dict


class Room(BaseModel):
    type: RoomType
    devices: Dict[str, DeviceStatus]


class WeatherType(str, Enum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"


class House(BaseModel):
    rooms: Dict[RoomType, Room]
    environment: Dict[str, float]
    time_of_day: float
    time_minutes: int = 0
    simulation_speed: float = 1.0
    weather: WeatherType = WeatherType.SUNNY
    days_passed: int = 0


class DeviceUpdateRequest(BaseModel):
    room: RoomType
    device_id: str
    status: Dict
