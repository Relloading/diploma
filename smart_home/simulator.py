import time
import math
import asyncio
from models import House, RoomType, DeviceType, DeviceStatus, Room
from typing import Dict, Optional
import random


class SmartHomeSimulator:
    def __init__(self):
        # Инициализация дома
        self.house = House(
            rooms={
                RoomType.BATHROOM: self._create_bathroom(),
                RoomType.KITCHEN: self._create_room(RoomType.KITCHEN),
                RoomType.BEDROOM: self._create_room(RoomType.BEDROOM),
                RoomType.LIVING_ROOM: self._create_room(RoomType.LIVING_ROOM),
            },
            environment={
                "outside_temp": 20.0,
                "outside_humidity": 50.0,
                "outside_light": 50.0,
            },
            time_of_day=12.0,  # Начинаем в полдень
        )
        
        self.running = False
        self.last_update = time.time()
        self.last_motion_room: Optional[RoomType] = None

    def _create_room(self, room_type: RoomType) -> Room:
        """Создает комнату с устройствами"""
        devices = {
            f"socket_{room_type}": DeviceStatus(
                id=f"socket_{room_type}",
                type=DeviceType.SOCKET,
                status={"power": False}
            ),
            f"camera_{room_type}": DeviceStatus(
                id=f"camera_{room_type}",
                type=DeviceType.CAMERA,
                status={"recording": False, "connected": False}
            ),
            f"light_{room_type}": DeviceStatus(
                id=f"light_{room_type}",
                type=DeviceType.LIGHT,
                status={"brightness": 0}
            ),
            f"curtain_{room_type}": DeviceStatus(
                id=f"curtain_{room_type}",
                type=DeviceType.CURTAIN,
                status={"open_percent": 0}
            ),
            f"window_{room_type}": DeviceStatus(
                id=f"window_{room_type}",
                type=DeviceType.WINDOW,
                status={"open_percent": 0}
            ),
            f"ac_{room_type}": DeviceStatus(
                id=f"ac_{room_type}",
                type=DeviceType.AC,
                status={"power": False, "mode": "cooling", "intensity": 0}
            ),
            f"climate_{room_type}": DeviceStatus(
                id=f"climate_{room_type}",
                type=DeviceType.CLIMATE,
                status={"power": False, "mode": "humidify", "intensity": 0}
            ),
            # Датчики
            f"temp_sensor_{room_type}": DeviceStatus(
                id=f"temp_sensor_{room_type}",
                type=DeviceType.TEMP_SENSOR,
                status={"temperature": 22.0}
            ),
            f"humidity_sensor_{room_type}": DeviceStatus(
                id=f"humidity_sensor_{room_type}",
                type=DeviceType.HUMIDITY_SENSOR,
                status={"humidity": 50.0}
            ),
            f"light_sensor_{room_type}": DeviceStatus(
                id=f"light_sensor_{room_type}",
                type=DeviceType.LIGHT_SENSOR,
                status={"light_level": 50.0}
            ),
            f"motion_sensor_{room_type}": DeviceStatus(
                id=f"motion_sensor_{room_type}",
                type=DeviceType.MOTION_SENSOR,
                status={"detected": False}
            ),
        }
        
        return Room(type=room_type, devices=devices)

    def _create_bathroom(self) -> Room:
        """Создает ванную комнату без окна, занавесок и камеры"""
        devices = {
            "socket_bathroom": DeviceStatus(
                id="socket_bathroom",
                type=DeviceType.SOCKET,
                status={"power": False}
            ),
            "light_bathroom": DeviceStatus(
                id="light_bathroom",
                type=DeviceType.LIGHT,
                status={"brightness": 0}
            ),
            "ac_bathroom": DeviceStatus(
                id="ac_bathroom",
                type=DeviceType.AC,
                status={"power": False, "mode": "cooling", "intensity": 0}
            ),
            "climate_bathroom": DeviceStatus(
                id="climate_bathroom",
                type=DeviceType.CLIMATE,
                status={"power": False, "mode": "humidify", "intensity": 0}
            ),
            # Датчики
            "temp_sensor_bathroom": DeviceStatus(
                id="temp_sensor_bathroom",
                type=DeviceType.TEMP_SENSOR,
                status={"temperature": 22.0}
            ),
            "humidity_sensor_bathroom": DeviceStatus(
                id="humidity_sensor_bathroom",
                type=DeviceType.HUMIDITY_SENSOR,
                status={"humidity": 65.0}
            ),
            "light_sensor_bathroom": DeviceStatus(
                id="light_sensor_bathroom",
                type=DeviceType.LIGHT_SENSOR,
                status={"light_level": 50.0}
            ),
            "motion_sensor_bathroom": DeviceStatus(
                id="motion_sensor_bathroom",
                type=DeviceType.MOTION_SENSOR,
                status={"detected": False}
            ),
        }
        
        return Room(type=RoomType.BATHROOM, devices=devices)

    def get_house_state(self) -> House:
        """Возвращает текущее состояние дома"""
        return self.house

    def update_device(self, room_type: RoomType, device_id: str, status: Dict) -> bool:
        """Обновляет состояние устройства"""
        if room_type not in self.house.rooms:
            return False
            
        room = self.house.rooms[room_type]
        
        if device_id not in room.devices:
            return False
            
        # Если это датчик движения и его включают
        if room.devices[device_id].type == DeviceType.MOTION_SENSOR and status.get("detected", False):
            # Отключаем датчики движения в других комнатах
            for r_type, r in self.house.rooms.items():
                for d_id, device in r.devices.items():
                    if device.type == DeviceType.MOTION_SENSOR and d_id != device_id:
                        device.status["detected"] = False
            self.last_motion_room = room_type

        # Если это розетка и к ней подключена камера
        if room.devices[device_id].type == DeviceType.SOCKET:
            camera_id = f"camera_{room_type}"
            if room_type != RoomType.BATHROOM and camera_id in room.devices:
                # Связываем состояние камеры с розеткой
                room.devices[camera_id].status["connected"] = status.get("power", False)
                # Если розетка выключена, камера не может вести запись
                if not status.get("power", True):
                    room.devices[camera_id].status["recording"] = False
        
        # Обновляем статус устройства
        room.devices[device_id].status.update(status)
        return True

    def set_simulation_speed(self, speed: float) -> None:
        """Устанавливает скорость симуляции"""
        if speed in [1.0, 15.0, 60.0]:
            self.house.simulation_speed = speed

    async def start_simulation(self):
        """Запускает симуляцию"""
        self.running = True
        self.last_update = time.time()
        
        while self.running:
            current_time = time.time()
            elapsed_real_time = current_time - self.last_update
            elapsed_sim_time = elapsed_real_time * self.house.simulation_speed
            
            # Обновляем время суток (цикл 24 часа)
            self.house.time_of_day = (self.house.time_of_day + elapsed_sim_time / 60) % 24
            
            # Обновляем внешние условия
            self._update_environment(elapsed_sim_time)
            
            # Обновляем состояние каждой комнаты
            for room_type, room in self.house.rooms.items():
                self._update_room(room_type, room, elapsed_sim_time)
            
            self.last_update = current_time
            await asyncio.sleep(1.0)  # Обновляем состояние каждую секунду

    def stop_simulation(self):
        """Останавливает симуляцию"""
        self.running = False

    def _update_environment(self, elapsed_time: float):
        """Обновляет внешние условия окружающей среды"""
        # Температура колеблется в зависимости от времени суток
        hour_temp_factor = math.sin((self.house.time_of_day - 6) * math.pi / 12)
        self.house.environment["outside_temp"] = 20 + 10 * hour_temp_factor
        
        # Освещенность зависит от времени суток
        # Максимум в полдень, минимум в полночь
        if 6 <= self.house.time_of_day <= 18:  # День
            daylight_factor = math.sin((self.house.time_of_day - 6) * math.pi / 12)
            self.house.environment["outside_light"] = 100 * daylight_factor
        else:  # Ночь
            self.house.environment["outside_light"] = 5  # Минимальная освещенность ночью
        
        # Случайные колебания влажности
        humidity_change = random.uniform(-0.5, 0.5) * elapsed_time / 60
        self.house.environment["outside_humidity"] = max(30, min(90, 
            self.house.environment["outside_humidity"] + humidity_change))

    def _update_room(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет состояние комнаты и её устройств"""
        # Обновление температуры
        self._update_temperature(room_type, room, elapsed_time)
        
        # Обновление влажности
        self._update_humidity(room_type, room, elapsed_time)
        
        # Обновление освещенности
        self._update_light_level(room_type, room)
        
        # Подключение/отключение устройств в зависимости от состояния розеток
        self._update_connected_devices(room_type, room)

    def _update_temperature(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет температуру в комнате"""
        temp_sensor_id = f"temp_sensor_{room_type}"
        window_id = f"window_{room_type}"
        ac_id = f"ac_{room_type}"
        
        current_temp = room.devices[temp_sensor_id].status["temperature"]
        outside_temp = self.house.environment["outside_temp"]
        
        # Влияние окна (только если оно есть в комнате)
        window_factor = 0
        if window_id in room.devices:
            window_percent = room.devices[window_id].status["open_percent"]
            window_factor = window_percent / 100.0
        
        # Влияние кондиционера
        ac_factor = 0
        if room.devices[ac_id].status["power"]:
            ac_intensity = room.devices[ac_id].status["intensity"] / 100.0
            if room.devices[ac_id].status["mode"] == "cooling":
                ac_factor = -ac_intensity * 10.0  # Охлаждение до -10 градусов
            else:
                ac_factor = ac_intensity * 10.0   # Нагрев до +10 градусов
        
        # Расчет новой температуры
        # Комнатная температура стремится к внешней через окно и к комфортной через кондиционер
        natural_change = (outside_temp - current_temp) * window_factor * 0.1 * elapsed_time / 60
        ac_change = ac_factor * 0.2 * elapsed_time / 60
        
        new_temp = current_temp + natural_change + ac_change
        room.devices[temp_sensor_id].status["temperature"] = round(new_temp, 1)

    def _update_humidity(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет влажность в комнате"""
        humidity_sensor_id = f"humidity_sensor_{room_type}"
        window_id = f"window_{room_type}"
        climate_id = f"climate_{room_type}"
        
        current_humidity = room.devices[humidity_sensor_id].status["humidity"]
        outside_humidity = self.house.environment["outside_humidity"]
        
        # Влияние окна
        window_factor = 0
        if window_id in room.devices:
            window_percent = room.devices[window_id].status["open_percent"]
            window_factor = window_percent / 100.0
        
        # Влияние климатического устройства
        climate_factor = 0
        if room.devices[climate_id].status["power"]:
            climate_intensity = room.devices[climate_id].status["intensity"] / 100.0
            if room.devices[climate_id].status["mode"] == "humidify":
                climate_factor = climate_intensity * 30.0  # Увлажнение до +30%
            else:
                climate_factor = -climate_intensity * 30.0  # Осушение до -30%
        
        # Расчет новой влажности
        natural_change = (outside_humidity - current_humidity) * window_factor * 0.1 * elapsed_time / 60
        climate_change = climate_factor * 0.2 * elapsed_time / 60
        
        new_humidity = current_humidity + natural_change + climate_change
        room.devices[humidity_sensor_id].status["humidity"] = round(max(10, min(99, new_humidity)), 1)

    def _update_light_level(self, room_type: RoomType, room: Room):
        """Обновляет уровень освещенности в комнате"""
        light_sensor_id = f"light_sensor_{room_type}"
        light_id = f"light_{room_type}"
        curtain_id = f"curtain_{room_type}"
        window_id = f"window_{room_type}"
        
        outside_light = self.house.environment["outside_light"]
        
        # Базовый свет от внутреннего освещения
        internal_light = room.devices[light_id].status["brightness"]
        
        # Внешний свет через окна
        external_light = 0
        if curtain_id in room.devices and window_id in room.devices:
            curtain_open = room.devices[curtain_id].status["open_percent"] / 100.0
            window_open = room.devices[window_id].status["open_percent"] / 100.0
            external_light = outside_light * curtain_open * (1 + window_open) / 2
        
        # Итоговый уровень освещенности
        total_light = min(100, internal_light + external_light)
        room.devices[light_sensor_id].status["light_level"] = round(total_light, 1)

    def _update_connected_devices(self, room_type: RoomType, room: Room):
        """Обновляет статусы устройств, подключенных к розеткам"""
        socket_id = f"socket_{room_type}"
        camera_id = f"camera_{room_type}"
        
        if socket_id in room.devices and camera_id in room.devices:
            socket_power = room.devices[socket_id].status["power"]
            room.devices[camera_id].status["connected"] = socket_power
            if not socket_power:
                room.devices[camera_id].status["recording"] = False
