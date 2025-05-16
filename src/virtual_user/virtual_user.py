import asyncio
import json
import random
import ollama
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("VirtualUser")


class UserState(str, Enum):
    HOME = "home"
    AWAY = "away"
    SLEEPING = "sleeping"


class VirtualUser:
    def __init__(self, model_name="llama3.1:latest"):
        self.model_name = model_name
        self.state = UserState.HOME
        self.current_room = "living_room"
        self.last_action_time = 0
        self.last_query_time = 0
        self.comfort_status = "I'm comfortable with the current home environment."
        self.is_active = False
        self.simulator = None

        self.schedule = {
            "wake_up": 2,
            "leave_home": 17,
            "return_home": 18,
            "go_to_bed": 23,
        }

        self.prompt_template = """
You are a virtual smart home resident. Your role is to interact with the smart home devices based on your needs and comfort. 

Current time: {time}
Current room: {room}
Weather outside: {weather}, Temperature: {temp}°C, Humidity: {humidity}%

Current state of devices in {room}:
{devices}

Current sensors in {room}:
{sensors}

Your preferences:
- Comfortable temperature: 21-23°C
- Preferred humidity: 40-60%
- Lighting: Bright during day, dim in evening
- You prefer fresh air but not when it's raining
- You like to sleep in a cool room (temperature of 16-18°C)
- When leaving home, you prefer to turn off most devices to save energy
- In the evening, you prefer warm, softer lighting

Think about your current comfort based on the sensor data and device states. 

Do you want to adjust any of the devices in this room to make yourself more comfortable? If yes, describe what changes you want to make. If you're comfortable, just say so.

Keep your answer short and focused on device adjustments or your comfort level only. No explanation needed.
"""

    async def start(self, smart_home_simulator):
        """Запуск виртуального пользователя"""
        self.simulator = smart_home_simulator
        self.is_active = True
        try:
            while self.is_active:
                house_state = self._get_house_state()
                if not house_state:
                    await asyncio.sleep(5)
                    continue

                current_hour = int(house_state.get("time_of_day", 0))
                current_minutes = house_state.get("time_minutes", 0)

                if self.last_action_time < current_minutes:
                    self.last_action_time = 0
                if house_state["days_passed"] > 6:
                    continue
                self._update_user_state(current_hour)

                if self.state == UserState.HOME:
                    if current_minutes - self.last_action_time >= 15:
                        await self._maybe_change_room(house_state)
                        self.last_action_time = current_minutes

                    if current_minutes // 20 > self.last_query_time // 20:
                        await self._on_room_changing(house_state)
                        self.last_query_time = current_minutes

                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in virtual user: {e}")
        finally:
            self.is_active = False

    def stop(self):
        """Остановка виртуального пользователя"""
        self.is_active = False

    def get_status(self):
        """Получение текущего статуса пользователя"""
        return {
            "state": self.state,
            "current_room": self.current_room,
            "comfort_status": self.comfort_status,
        }

    async def _on_room_changing(self, house_state):
        self.comfort_status = await self._query_user_comfort(house_state)

        await self._apply_user_preferences(self.comfort_status, house_state)

    def _get_house_state(self):
        """Получение текущего состояния дома через API"""
        return self.simulator.get_house_state().model_dump()

    def _update_device(self, room, device_id, status):
        """Обновление состояния устройства через API"""
        try:
            success = self.simulator.update_device(room, device_id, status)
            return success
        except Exception as e:
            logger.error(f"Failed to update device: {e}")
            return None

    def _update_user_state(self, current_hour):
        """Обновление состояния пользователя на основе времени"""
        if self.schedule["wake_up"] <= current_hour < self.schedule["leave_home"]:
            if self.state != UserState.HOME:
                logger.info(f"User is waking up and staying home at {current_hour}:00")
                self.state = UserState.HOME
                self.current_room = "bedroom"
                self._perform_routine_actions("wake_up")

        elif self.schedule["leave_home"] <= current_hour < self.schedule["return_home"]:
            if self.state != UserState.AWAY:
                logger.info(f"User is leaving home at {current_hour}:00")
                self.state = UserState.AWAY
                self._perform_routine_actions("leave_home")

        elif self.schedule["return_home"] <= current_hour < self.schedule["go_to_bed"]:
            if self.state != UserState.HOME:
                logger.info(f"User is returning home at {current_hour}:00")
                self.state = UserState.HOME
                self.current_room = "living_room"
                self._perform_routine_actions("return_home")

        elif (
            current_hour >= self.schedule["go_to_bed"]
            or current_hour < self.schedule["wake_up"]
        ):
            if self.state != UserState.SLEEPING:
                logger.info(f"User is going to bed at {current_hour}:00")
                self.state = UserState.SLEEPING
                self.current_room = "bedroom"
                self._perform_routine_actions("go_to_bed")

    async def _maybe_change_room(self, house_state):
        """Случайное перемещение между комнатами"""
        if self.state != UserState.HOME:
            return

        rooms = ["living_room", "kitchen", "bathroom", "bedroom"]
        possible_rooms = [r for r in rooms if r != self.current_room]

        if random.random() < 0.4:
            new_room = random.choice(possible_rooms)
            logger.info(f"User is moving from {self.current_room} to {new_room}")

            self._update_device(
                self.current_room,
                f"motion_sensor_{self.current_room}",
                {"detected": False},
            )

            self.current_room = new_room

            self._update_device(
                new_room, f"motion_sensor_{new_room}", {"detected": True}
            )

            await self._on_room_changing(house_state)

    async def _query_user_comfort(self, house_state):
        """Запрос к виртуальному пользователю о комфорте"""
        if self.state != UserState.HOME:
            return "I'm not at home."

        if self.state == UserState.SLEEPING:
            return "I'm sleeping."

        room_data = house_state["rooms"].get(self.current_room, {})
        devices_info = []
        sensors_info = []

        for device_id, device in room_data.get("devices", {}).items():
            if "sensor" in device_id:
                sensor_status = self._format_status_for_prompt(device)
                sensors_info.append(f"- {device_id}: {sensor_status}")
            else:
                device_status = self._format_status_for_prompt(device)
                devices_info.append(f"- {device_id}: {device_status}")

        hours = int(house_state["time_of_day"])
        minutes = int((house_state["time_of_day"] - hours) * 60)
        time_str = f"{hours:02d}:{minutes:02d}"

        prompt = self.prompt_template.format(
            time=time_str,
            room=self.current_room,
            weather=house_state.get("weather", "unknown"),
            temp=house_state["environment"]["outside_temp"],
            humidity=house_state["environment"]["outside_humidity"],
            devices="\n".join(devices_info),
            sensors="\n".join(sensors_info),
        )

        try:
            response = ollama.chat(
                model=self.model_name, messages=[{"role": "user", "content": prompt}]
            )

            comfort_response = response["message"]["content"].strip()
            logger.info(f"User comfort query response: {comfort_response}")
            return comfort_response

        except Exception as e:
            logger.error(f"Failed to query LLM: {e}")
            return "I'm having trouble deciding what I need."

    def _perform_routine_actions(self, state_change=None):
        """Выполнение рутинных действий при изменении состояния"""
        if state_change == "wake_up":
            self._update_device("bedroom", "light_bedroom", {"brightness": 60})
            self._update_device("bedroom", "curtain_bedroom", {"open_percent": 70})
            self._update_device("bedroom", "motion_sensor_bedroom", {"detected": False})
            self._update_device("kitchen", "motion_sensor_kitchen", {"detected": True})
            self.current_room = "kitchen"
            self._update_device("kitchen", "light_kitchen", {"brightness": 80})
            logger.info("Performed wake up routine")

        elif state_change == "leave_home":
            for room in ["living_room", "kitchen", "bathroom", "bedroom"]:
                self._update_device(room, f"motion_sensor_{room}", {"detected": False})

            for room in ["living_room", "kitchen", "bathroom", "bedroom"]:
                self._update_device(room, f"light_{room}", {"brightness": 0})
                if room != "bathroom":  # В ванной нет окна
                    self._update_device(room, f"window_{room}", {"open_percent": 0})
                    self._update_device(room, f"curtain_{room}", {"open_percent": 0})

            logger.info("Performed leave home routine")

        elif state_change == "return_home":
            self._update_device(
                "living_room", "motion_sensor_living_room", {"detected": True}
            )

            current_hour = datetime.now().hour
            brightness = 80 if current_hour < 20 else 50
            self._update_device(
                "living_room", "light_living_room", {"brightness": brightness}
            )

            logger.info("Performed return home routine")

        elif state_change == "go_to_bed":
            for room in ["living_room", "kitchen", "bathroom"]:
                self._update_device(room, f"light_{room}", {"brightness": 0})
                self._update_device(room, f"motion_sensor_{room}", {"detected": False})

            self._update_device("bedroom", "motion_sensor_bedroom", {"detected": True})
            self._update_device("bedroom", "light_bedroom", {"brightness": 20})
            self._update_device("bedroom", "curtain_bedroom", {"open_percent": 0})

            self._update_device(
                "bedroom",
                "ac_bedroom",
                {"power": True, "mode": "cooling", "intensity": 40},
            )

            logger.info("Performed go to bed routine")

    def _format_status_for_prompt(self, device):
        """Форматирование статуса устройства для промпта с проверкой безопасности"""
        try:
            status_str = []

            for key, value in device.get("status", {}).items():
                try:
                    if key == "power" or key == "recording" or key == "detected":
                        status_str.append(f"{key}: {'on' if value else 'off'}")
                    elif (
                        key == "brightness"
                        or key == "intensity"
                        or key == "open_percent"
                    ):
                        status_str.append(f"{key}: {value}%")
                    elif key == "temperature":
                        status_str.append(f"{key}: {value}°C")
                    elif key == "humidity" or key == "light_level":
                        status_str.append(f"{key}: {value}%")
                    else:
                        str_value = str(value)
                        if len(str_value) > 100:
                            str_value = str_value[:97] + "..."
                        status_str.append(f"{key}: {str_value}")
                except Exception as e:
                    logger.warning(f"Error formatting status value for key {key}: {e}")
                    status_str.append(f"{key}: [error]")

            return ", ".join(status_str)

        except Exception as e:
            logger.error(f"Error formatting device status: {e}")
            return "[error formatting status]"

    async def _apply_user_preferences(self, comfort_response, house_state):
        """Применение предпочтений пользователя на основе ответа LLM"""
        if any(
            word in comfort_response.lower()
            for word in ["comfortable", "fine", "good", "ok", "okay"]
        ):
            return

        parse_prompt = f"""
    Given the user's request about their comfort in the smart home:
    "{comfort_response}"

    Extract specific device adjustments needed. The user is in the {self.current_room} room.

    Available devices in this room are:
    - light_{self.current_room}: Controls brightness (0-100)
    - {'' if self.current_room == 'bathroom' else f"window_{self.current_room}: Controls window opening (0-100%), field name - open_percent"}
    - {'' if self.current_room == 'bathroom' else f"curtain_{self.current_room}: Controls curtain opening (0-100%), field name - open_percent"}
    - ac_{self.current_room}: Controls air conditioning (target_temp: integer, intensity: 0-100)
    - climate_{self.current_room}: Controls humidity (target_humidity: 0-100, intensity: 0-100)

    Format your response as a JSON array of actions. For example:
    [
    {{"device": "light_living_room", "status": {{"brightness": 80}} }},
    {{"device": "ac_living_room", "status": {{"power": true, "target_temp": 22, "intensity": 50}} }}
    ]

    Return ONLY valid JSON, nothing else. If no clear adjustments are needed, return an empty array [].
    """

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": parse_prompt}],
            )

            actions_text = response["message"]["content"].strip()

            import re

            json_match = re.search(
                r"```json\n([\s\S]*?)\n```|```([\s\S]*?)```|\[([\s\S]*?)\]|(\{[\s\S]*?\})",
                actions_text,
            )

            if json_match:
                json_str = next(
                    group for group in json_match.groups() if group is not None
                )
                if not json_str.strip().startswith("["):
                    json_str = f"[{json_str}]"
            else:
                json_str = actions_text

            try:
                actions = json.loads(json_str)

                if isinstance(actions, dict):
                    actions = [actions]

                logger.info(f"Parsed actions: {actions}")

                for action in actions:
                    device_id = action.get("device")
                    status = action.get("status")

                    if device_id and status:
                        logger.info(f"Updating device {device_id} with status {status}")
                        self._update_device(self.current_room, device_id, status)

            except json.JSONDecodeError:
                logger.error(f"Failed to parse actions JSON: {json_str}")

        except Exception as e:
            logger.error(f"Failed to apply user preferences: {e}")
