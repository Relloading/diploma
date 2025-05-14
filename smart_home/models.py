from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Literal


class DeviceType(str, Enum):
    SOCKET = "socket"
    CAMERA = "camera"
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
    
    
class House(BaseModel):
    rooms: Dict[RoomType, Room]
    environment: Dict[str, float]
    time_of_day: float  # 0-24 hours
    simulation_speed: float = 1.0  # 1.0, 15.0, or 60.0


class DeviceUpdateRequest(BaseModel):
    room: RoomType
    device_id: str
    status: Dict
