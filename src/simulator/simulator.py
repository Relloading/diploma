from datetime import datetime
import time
import math
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from .models import House, RoomType, DeviceType, DeviceStatus, Room, WeatherType
from typing import Dict, Optional
import random
import logging
import os

logger = logging.getLogger(__name__)


class SmartHomeSimulator:
    def __init__(self):
        initial_time_of_day = 1.0
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
            time_of_day=initial_time_of_day,
            time_minutes=int(initial_time_of_day * 60),
            weather=WeatherType.SUNNY,
            simulation_speed=1.0,
        )

        self.running = False
        self.last_update = time.time()
        self.last_motion_room: Optional[RoomType] = None
        self.weather_change_counter = 0

        self.sensor_data = self._initialize_sensor_logs()

        os.makedirs("reports", exist_ok=True)

    def _initialize_sensor_logs(self) -> Dict:
        """Инициализирует структуру для хранения логов датчиков"""
        data = {}
        for room_type in RoomType:
            data[room_type.value] = {
                "time": [],
                "temperature": [],
                "humidity": [],
                "light": [],
            }
        return data

    def _log_sensor_data(self):
        """Записывает текущие показания датчиков в логи"""
        current_time = self.house.time_minutes

        for room_type, room in self.house.rooms.items():
            temp = room.devices.get(f"temp_sensor_{room_type.value}").status.get(
                "temperature", 0
            )
            humidity = room.devices.get(
                f"humidity_sensor_{room_type.value}"
            ).status.get("humidity", 0)
            light = room.devices.get(f"light_sensor_{room_type.value}").status.get(
                "light_level", 0
            )

            room_data = self.sensor_data[room_type.value]
            room_data["time"].append(current_time)
            room_data["temperature"].append(temp)
            room_data["humidity"].append(humidity)
            room_data["light"].append(light)

    def _generate_reports(self):
        """Генерирует отчеты (графики и CSV) за день"""
        day = self.house.days_passed
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = f"reports/day_{day}_{timestamp}"
        os.makedirs(report_dir, exist_ok=True)

        logger.info(f"Generating reports for day {day} in {report_dir}")

        for room_type in RoomType:
            room_name = room_type.value
            room_data = self.sensor_data[room_name]

            formatted_time = [f"{t//60:02d}:{t%60:02d}" for t in room_data["time"]]

            df = pd.DataFrame(
                {
                    "time": formatted_time,
                    "time_minutes": room_data["time"],
                    "temperature": room_data["temperature"],
                    "humidity": room_data["humidity"],
                    "light": room_data["light"],
                }
            )

            csv_path = f"{report_dir}/{room_name}_data.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"CSV report saved to {csv_path}")

            self._create_plots(room_name, room_data, report_dir)

        self._create_comparison_plots(report_dir)

        self.sensor_data = self._initialize_sensor_logs()

    def _create_plots(self, room_name: str, room_data: Dict, report_dir: str):
        """Создаёт графики для одной комнаты"""
        time_hours = [t / 60 for t in room_data["time"]]

        plt.figure(figsize=(10, 6))
        plt.plot(time_hours, room_data["temperature"])
        plt.title(f"Temperature in {room_name}")
        plt.xlabel("Time (hours)")
        plt.ylabel("Temperature (°C)")
        plt.grid(True)
        plt.savefig(f"{report_dir}/{room_name}_temperature.png")
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(time_hours, room_data["humidity"])
        plt.title(f"Humidity in {room_name}")
        plt.xlabel("Time (hours)")
        plt.ylabel("Humidity (%)")
        plt.grid(True)
        plt.savefig(f"{report_dir}/{room_name}_humidity.png")
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(time_hours, room_data["light"])
        plt.title(f"Light level in {room_name}")
        plt.xlabel("Time (hours)")
        plt.ylabel("Light level (%)")
        plt.grid(True)
        plt.savefig(f"{report_dir}/{room_name}_light.png")
        plt.close()

    def _create_comparison_plots(self, report_dir: str):
        """Создаёт сравнительные графики для всех комнат"""
        plt.figure(figsize=(12, 7))
        for room_type in RoomType:
            room_name = room_type.value
            time_hours = [t / 60 for t in self.sensor_data[room_name]["time"]]
            plt.plot(
                time_hours, self.sensor_data[room_name]["temperature"], label=room_name
            )
        plt.title("Temperature Comparison Between Rooms")
        plt.xlabel("Time (hours)")
        plt.ylabel("Temperature (°C)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{report_dir}/temperature_comparison.png")
        plt.close()

        plt.figure(figsize=(12, 7))
        for room_type in RoomType:
            room_name = room_type.value
            time_hours = [t / 60 for t in self.sensor_data[room_name]["time"]]
            plt.plot(
                time_hours, self.sensor_data[room_name]["humidity"], label=room_name
            )
        plt.title("Humidity Comparison Between Rooms")
        plt.xlabel("Time (hours)")
        plt.ylabel("Humidity (%)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{report_dir}/humidity_comparison.png")
        plt.close()

        plt.figure(figsize=(12, 7))
        for room_type in RoomType:
            room_name = room_type.value
            time_hours = [t / 60 for t in self.sensor_data[room_name]["time"]]
            plt.plot(time_hours, self.sensor_data[room_name]["light"], label=room_name)
        plt.title("Light Level Comparison Between Rooms")
        plt.xlabel("Time (hours)")
        plt.ylabel("Light level (%)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{report_dir}/light_comparison.png")
        plt.close()

    def set_simulation_speed(self, speed: float) -> bool:
        """Устанавливает скорость симуляции"""
        if speed not in [1.0, 15.0, 60.0]:
            logger.warning(
                f"Invalid simulation speed: {speed}. Must be 1.0, 15.0, 60.0"
            )
            return False

        logger.info(f"Setting simulation speed to {speed}x")
        self.house.simulation_speed = speed
        return True

    def set_weather(self, weather: WeatherType) -> bool:
        """Устанавливает погоду вручную"""
        if weather not in [WeatherType.SUNNY, WeatherType.CLOUDY, WeatherType.RAINY]:
            return False
        self.house.weather = weather
        return True

    def get_simulation_time(self):
        """Возвращает текущее время симуляции"""
        return {
            "time_of_day": self.house.time_of_day,
            "time_seconds": self.house.time_seconds,
        }

    def _create_room(self, room_type: RoomType) -> Room:
        """Создает комнату с устройствами"""

        room_value = room_type.value

        devices = {
            f"light_{room_value}": DeviceStatus(
                id=f"light_{room_value}",
                type=DeviceType.LIGHT,
                status={"brightness": 0},
            ),
            f"curtain_{room_value}": DeviceStatus(
                id=f"curtain_{room_value}",
                type=DeviceType.CURTAIN,
                status={"open_percent": 0},
            ),
            f"window_{room_value}": DeviceStatus(
                id=f"window_{room_value}",
                type=DeviceType.WINDOW,
                status={"open_percent": 0},
            ),
            f"ac_{room_value}": DeviceStatus(
                id=f"ac_{room_value}",
                type=DeviceType.AC,
                status={"power": False, "target_temp": 22, "intensity": 10},
            ),
            f"climate_{room_value}": DeviceStatus(
                id=f"climate_{room_value}",
                type=DeviceType.CLIMATE,
                status={"power": False, "target_humidity": 50, "intensity": 10},
            ),
            f"temp_sensor_{room_value}": DeviceStatus(
                id=f"temp_sensor_{room_value}",
                type=DeviceType.TEMP_SENSOR,
                status={"temperature": 22.0},
            ),
            f"humidity_sensor_{room_value}": DeviceStatus(
                id=f"humidity_sensor_{room_value}",
                type=DeviceType.HUMIDITY_SENSOR,
                status={"humidity": 50.0},
            ),
            f"light_sensor_{room_value}": DeviceStatus(
                id=f"light_sensor_{room_value}",
                type=DeviceType.LIGHT_SENSOR,
                status={"light_level": 50.0},
            ),
            f"motion_sensor_{room_value}": DeviceStatus(
                id=f"motion_sensor_{room_value}",
                type=DeviceType.MOTION_SENSOR,
                status={"detected": False},
            ),
        }

        return Room(type=room_type, devices=devices)

    def _create_bathroom(self) -> Room:
        """Создает ванную комнату без окна, занавесок и камеры"""
        devices = {
            "light_bathroom": DeviceStatus(
                id="light_bathroom",
                type=DeviceType.LIGHT.value,
                status={"brightness": 0},
            ),
            f"ac_bathroom": DeviceStatus(
                id=f"ac_bathroom",
                type=DeviceType.AC,
                status={
                    "power": True,
                    "target_temp": 22,
                    "intensity": 30,
                },
            ),
            f"climate_bathroom": DeviceStatus(
                id=f"climate_bathroom",
                type=DeviceType.CLIMATE,
                status={
                    "power": False,
                    "target_humidity": 50,
                    "intensity": 30,
                },
            ),
            "temp_sensor_bathroom": DeviceStatus(
                id="temp_sensor_bathroom",
                type=DeviceType.TEMP_SENSOR.value,
                status={"temperature": 22.0},
            ),
            "humidity_sensor_bathroom": DeviceStatus(
                id="humidity_sensor_bathroom",
                type=DeviceType.HUMIDITY_SENSOR.value,
                status={"humidity": 65.0},
            ),
            "light_sensor_bathroom": DeviceStatus(
                id="light_sensor_bathroom",
                type=DeviceType.LIGHT_SENSOR.value,
                status={"light_level": 50.0},
            ),
            "motion_sensor_bathroom": DeviceStatus(
                id="motion_sensor_bathroom",
                type=DeviceType.MOTION_SENSOR.value,
                status={"detected": False},
            ),
        }

        return Room(type=RoomType.BATHROOM, devices=devices)

    def get_house_state(self) -> House:
        """Возвращает текущее состояние дома с проверкой целостности"""
        return self.house

    def update_device(self, room_type: RoomType, device_id: str, status: Dict) -> bool:
        """Обновляет состояние устройства с валидацией входящих данных"""
        try:
            if not isinstance(room_type, RoomType) and not isinstance(room_type, str):
                logger.error(f"Invalid room type: {room_type}")
                return False

            if isinstance(room_type, str):
                try:
                    room_type = RoomType(room_type)
                except ValueError:
                    logger.error(f"Invalid room type: {room_type}")
                    return False

            if room_type not in self.house.rooms:
                logger.error(f"Room not found: {room_type}")
                return False

            room = self.house.rooms[room_type]

            if not isinstance(device_id, str) or device_id not in room.devices:
                logger.error(f"Device not found: {device_id} in room {room_type}")
                return False

            if not isinstance(status, dict):
                logger.error(f"Invalid status format for device {device_id}: {status}")
                return False

            device = room.devices[device_id]

            device_type = device.type
            if isinstance(device_type, str):
                try:
                    device_type = DeviceType(device_type)
                except ValueError:
                    logger.error(f"Invalid device type: {device_type}")
                    return False

            if not self._validate_device_status(device_type, status, device.status):
                logger.error(f"Invalid status values for device {device_id}: {status}")
                return False

            if device_type == DeviceType.MOTION_SENSOR and status.get(
                "detected", False
            ):
                for _, r in self.house.rooms.items():
                    for d_id, d in r.devices.items():
                        if d.type == DeviceType.MOTION_SENSOR and d_id != device_id:
                            d.status["detected"] = False
                self.last_motion_room = room_type

            for key in status:
                if key in device.status:
                    device.status[key] = status[key]
                else:
                    logger.warning(
                        f"Ignoring unknown property '{key}' for device {device_id}"
                    )

            return True

        except Exception as e:
            logger.error(f"Error updating device {device_id}: {e}")
            return False

    def _validate_device_status(
        self, device_type: DeviceType, new_status: Dict, current_status: Dict
    ) -> bool:
        """
        Валидирует статус устройства в зависимости от его типа

        Args:
            device_type: Тип устройства
            new_status: Новый статус, который будет применен
            current_status: Текущий статус устройства

        Returns:
            bool: True, если статус валиден, False в противном случае
        """
        try:
            logger.debug(
                f"Validating device status for type: {device_type}, status: {new_status}"
            )

            if isinstance(device_type, str):
                try:
                    device_type = DeviceType(device_type)
                    logger.debug(f"Converted string device type to enum: {device_type}")
                except ValueError:
                    logger.error(f"Invalid device type string: {device_type}")
                    return False

            for key in new_status:
                if key not in current_status:
                    logger.error(
                        f"Property '{key}' is not allowed for device type {device_type}"
                    )
                    return False

            if device_type == DeviceType.LIGHT:
                if "brightness" in new_status:
                    if not isinstance(new_status["brightness"], (int, float)):
                        logger.error(
                            f"'brightness' must be a number for device type {device_type}"
                        )
                        return False
                    if new_status["brightness"] < 0 or new_status["brightness"] > 100:
                        logger.error(
                            f"'brightness' must be between 0 and 100 for device type {device_type}"
                        )
                        return False

            elif device_type in [DeviceType.CURTAIN, DeviceType.WINDOW]:
                if "open_percent" in new_status:
                    if not isinstance(new_status["open_percent"], (int, float)):
                        logger.error(
                            f"'open_percent' must be a number for device type {device_type}"
                        )
                        return False
                    if (
                        new_status["open_percent"] < 0
                        or new_status["open_percent"] > 100
                    ):
                        logger.error(
                            f"'open_percent' must be between 0 and 100 for device type {device_type}"
                        )
                        return False

            elif device_type == DeviceType.AC:
                if "power" in new_status and not isinstance(new_status["power"], bool):
                    logger.error(
                        f"'power' must be boolean for device type {device_type}"
                    )
                    return False
                if "target_temp" in new_status and not isinstance(
                    new_status["target_temp"], (int, float)
                ):
                    logger.error(
                        f"'target_temp' must be digital for device type {device_type}"
                    )
                    return False
                if "intensity" in new_status:
                    if not isinstance(new_status["intensity"], (int, float)):
                        logger.error(
                            f"'intensity' must be a number for device type {device_type}"
                        )
                        return False
                    if new_status["intensity"] < 0 or new_status["intensity"] > 100:
                        logger.error(
                            f"'intensity' must be between 0 and 100 for device type {device_type}"
                        )
                        return False

            elif device_type == DeviceType.CLIMATE:
                if "power" in new_status and not isinstance(new_status["power"], bool):
                    logger.error(
                        f"'power' must be boolean for device type {device_type}"
                    )
                    return False
                if "target_humidity" in new_status and not isinstance(
                    new_status["target_humidity"], (int, float)
                ):
                    logger.error(
                        f"'target_humidity' must be digital for device type {device_type}"
                    )
                    return False
                if "intensity" in new_status:
                    if not isinstance(new_status["intensity"], (int, float)):
                        logger.error(
                            f"'intensity' must be a number for device type {device_type}"
                        )
                        return False
                    if new_status["intensity"] < 0 or new_status["intensity"] > 100:
                        logger.error(
                            f"'intensity' must be between 0 and 100 for device type {device_type}"
                        )
                        return False

            elif device_type == DeviceType.MOTION_SENSOR:
                if "detected" in new_status and not isinstance(
                    new_status["detected"], bool
                ):
                    logger.error(
                        f"'detected' must be boolean for device type {device_type}"
                    )
                    return False

            elif device_type in [
                DeviceType.TEMP_SENSOR,
                DeviceType.HUMIDITY_SENSOR,
                DeviceType.LIGHT_SENSOR,
            ]:
                if new_status:
                    logger.warning(
                        f"Cannot update sensor device type {device_type} manually"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating device status for type {device_type}: {e}")
            return False

    async def start_simulation(self):
        """Запускает симуляцию"""
        self.running = True
        self.last_update = time.time()
        last_day_time = 0

        while self.running:
            current_time = time.time()
            elapsed_sim_time = 1
            self._log_sensor_data()
            minutes_in_day = 1440
            current_minutes = self.house.time_of_day * 60
            new_minutes = current_minutes + (elapsed_sim_time)

            if int(new_minutes / minutes_in_day) > int(last_day_time / minutes_in_day):
                self.house.days_passed += 1
                logger.info(f"New day started: Day {self.house.days_passed}")
                self._on_day_change()

            last_day_time = new_minutes

            new_minutes = new_minutes % minutes_in_day

            self.house.time_of_day = new_minutes / 60
            self.house.time_minutes = int(new_minutes)

            self._update_environment(elapsed_sim_time)

            for room_type, room in self.house.rooms.items():
                self._update_room(room_type, room, elapsed_sim_time)

            self.last_update = current_time
            await asyncio.sleep(1.0 / self.house.simulation_speed)

    def _on_day_change(self):
        """Обработчик события смены дня"""
        self._generate_reports()

    def stop_simulation(self):
        """Останавливает симуляцию"""
        if any(len(self.sensor_data[room]["time"]) > 0 for room in self.sensor_data):
            self._generate_reports()
        self.running = False

    def _update_environment(self, elapsed_time: float):
        """Обновляет внешние условия окружающей среды (время в минутах)"""
        self.weather_change_counter += elapsed_time
        if self.weather_change_counter >= 60:
            self.weather_change_counter = 0
            if random.random() < 0.1:
                current_weather = self.house.weather
                weather_options = [w for w in list(WeatherType) if w != current_weather]
                self.house.weather = random.choice(weather_options)

        hour_temp_factor = math.sin((self.house.time_of_day - 6) * math.pi / 12)
        base_temp = 20 + 10 * hour_temp_factor

        if self.house.weather == WeatherType.CLOUDY:
            base_temp -= 3
        elif self.house.weather == WeatherType.RAINY:
            base_temp -= 5

        self.house.environment["outside_temp"] = base_temp

        if 6 <= self.house.time_of_day <= 18:  # День
            daylight_factor = math.sin((self.house.time_of_day - 6) * math.pi / 12)
            base_light = 100 * daylight_factor

            if self.house.weather == WeatherType.CLOUDY:
                base_light *= 0.6
            elif self.house.weather == WeatherType.RAINY:
                base_light *= 0.4

            self.house.environment["outside_light"] = base_light
        else:
            self.house.environment["outside_light"] = 5

        base_humidity_change = random.uniform(-0.1, 0.1) * elapsed_time

        if self.house.weather == WeatherType.RAINY:
            base_humidity_change += 0.2 * elapsed_time

        self.house.environment["outside_humidity"] = max(
            30,
            min(90, self.house.environment["outside_humidity"] + base_humidity_change),
        )

    def _update_room(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет состояние комнаты и её устройств"""
        self._update_temperature(room_type, room, elapsed_time)

        self._update_humidity(room_type, room, elapsed_time)

        self._update_light_level(room_type, room)

    def _update_temperature(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет температуру в комнате (время в минутах)"""
        temp_sensor_id = f"temp_sensor_{room_type.value}"
        window_id = f"window_{room_type.value}"
        ac_id = f"ac_{room_type.value}"

        current_temp = room.devices[temp_sensor_id].status["temperature"]

        outside_temp = self.house.environment["outside_temp"]

        window_factor = 0
        if window_id in room.devices:
            window_percent = room.devices[window_id].status["open_percent"]
            window_factor = window_percent / 100.0

        ac_factor = 0
        if room.devices[ac_id].status["power"]:
            ac_status = room.devices[ac_id].status
            ac_intensity = ac_status["intensity"] / 100.0
            ac_target = ac_status["target_temp"]
            ac_diff = abs(current_temp - ac_target)
            ac_factor = ac_diff * ac_intensity * 0.05 * elapsed_time
            if ac_target < current_temp:
                ac_factor = -ac_factor

        natural_change = (
            (outside_temp - current_temp) * window_factor * 0.005 * elapsed_time
        )

        new_temp = current_temp + natural_change + ac_factor

        diff = abs(current_temp - outside_temp) * 0.002 * elapsed_time

        if new_temp > outside_temp:
            new_temp -= diff
        else:
            new_temp += diff

        room.devices[temp_sensor_id].status["temperature"] = new_temp

    def _update_humidity(self, room_type: RoomType, room: Room, elapsed_time: float):
        """Обновляет влажность в комнате (время в минутах)"""
        humidity_sensor_id = f"humidity_sensor_{room_type.value}"
        window_id = f"window_{room_type.value}"
        climate_id = f"climate_{room_type.value}"

        current_humidity = room.devices[humidity_sensor_id].status["humidity"]
        outside_humidity = self.house.environment["outside_humidity"]

        window_factor = 0
        if window_id in room.devices:
            window_percent = room.devices[window_id].status["open_percent"]
            window_factor = window_percent / 100.0

        climate_factor = 0
        if room.devices[climate_id].status["power"]:
            climate_status = room.devices[climate_id].status
            climate_intensity = climate_status["intensity"] / 100.0
            climate_target = climate_status["target_humidity"]
            climate_diff = abs(current_humidity - climate_target)
            climate_factor = climate_diff * climate_intensity * 0.05 * elapsed_time
            if climate_target < current_humidity:
                climate_factor = -climate_factor

        natural_change = (
            (outside_humidity - current_humidity) * window_factor * 0.005 * elapsed_time
        )

        new_humidity = current_humidity + natural_change + climate_factor

        diff = abs(current_humidity - outside_humidity) * 0.004 * elapsed_time

        if new_humidity > outside_humidity:
            new_humidity -= diff
        else:
            new_humidity += diff

        room.devices[humidity_sensor_id].status["humidity"] = max(
            10, min(99, new_humidity)
        )

    def _update_light_level(self, room_type: RoomType, room: Room):
        """Обновляет уровень освещенности в комнате"""
        light_sensor_id = f"light_sensor_{room_type.value}"
        light_id = f"light_{room_type.value}"
        curtain_id = f"curtain_{room_type.value}"
        window_id = f"window_{room_type.value}"

        outside_light = self.house.environment["outside_light"]

        internal_light = room.devices[light_id].status["brightness"]

        external_light = 0
        if curtain_id in room.devices and window_id in room.devices:
            curtain_open = room.devices[curtain_id].status["open_percent"] / 100.0
            window_open = room.devices[window_id].status["open_percent"] / 100.0
            external_light = outside_light * curtain_open * (1 + window_open) / 2

        total_light = min(100, internal_light + external_light)
        room.devices[light_sensor_id].status["light_level"] = round(total_light, 1)
