import ollama
import logging
import asyncio
import json
import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LLMAgent")


class LLMSmartHomeAgent:
    def __init__(self, model_name="llama3.1_2:latest"):
        self.model_name = model_name
        self.is_active = False
        self.observation_day = True
        self.user_actions = []
        self.last_check_time = 0
        self.simulator = None
        self.last_action_time = {}

    async def start(self, smart_home_simulator):
        """Запуск LLM агента"""
        self.is_active = True
        self.simulator = smart_home_simulator
        logger.info(
            f"LLM Smart Home Agent started. Observation day: {self.observation_day}"
        )

        try:
            while self.is_active:
                house_state = self.simulator.get_house_state()
                if self.last_check_time > house_state.time_minutes:
                    self.last_check_time = 0
                if not house_state:
                    logger.warning(
                        "No data from smart home proveded, possible system is down before Agent"
                    )
                    await asyncio.sleep(0.1)
                    continue

                if house_state.days_passed > 6 and self.observation_day:
                    self.observation_day = False
                    logger.info("First day completed. Switching to control mode.")

                current_time = house_state.time_minutes + house_state.days_passed * 1440
                if current_time - self.last_check_time >= 15:
                    self.last_check_time = current_time

                    if self.observation_day:
                        self._record_user_actions(house_state)
                    else:
                        await self._reproduce_actions(house_state)

                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in LLM agent: {e}")
        finally:
            self.is_active = False

    def stop(self):
        """Остановка LLM агента"""
        self.is_active = False
        logger.info("LLM Smart Home Agent stopped")

    def _record_user_actions(self, house_state):
        """Запись действий пользователя в день наблюдения"""
        current_time_of_day = house_state.time_minutes

        for room_type, room in house_state.rooms.items():
            for device_id, device in room.devices.items():
                if "sensor" in device_id:
                    continue

                device_key = f"{room_type}_{device_id}"

                if device_key not in self.last_action_time or self._is_device_changed(
                    device_key, device.status
                ):
                    action = {
                        "time_of_day": current_time_of_day,
                        "room": room_type,
                        "device_id": device_id,
                        "status": device.status.copy(),
                        "environment": self._get_environment_snapshot(house_state),
                    }

                    self.user_actions.append(action)
                    self.last_action_time[device_key] = device.status.copy()

                    logger.info(
                        f"Recorded user action: {room_type} - {device_id} - {device.status}"
                    )

    async def _reproduce_actions(self, house_state):
        """Воспроизведение действий пользователя на основе наблюдений"""
        try:
            current_time_of_day = house_state.time_minutes

            actions_to_perform = []
            time_window = 15

            for action in self.user_actions:
                if abs(action["time_of_day"] - current_time_of_day) <= time_window:
                    actions_to_perform.append(action)

            if not actions_to_perform:
                logger.info("No actiors found to perform")
            else:
                logger.info(
                    f"Found {len(actions_to_perform)} actions to potentially perform at time {self._format_time(house_state.time_minutes)}"
                )
                current_environment = self._get_environment_snapshot(house_state)

                actions_to_take = await self._get_llm_recommendations(
                    actions_to_perform, house_state, current_environment
                )

                if not actions_to_take:
                    logger.info("No actions to take at this time")
                    return

                logger.info(f"Will perform {len(actions_to_take)} actions")

                for action in actions_to_take:
                    try:
                        if not all(
                            k in action for k in ["room", "device_id", "status"]
                        ):
                            logger.warning(f"Skipping incomplete action: {action}")
                            continue

                        room = action["room"]
                        device_id = action["device_id"]
                        status = action["status"]

                        logger.info(
                            f"Attempting to apply action: {room} - {device_id} - {status}"
                        )
                        success = self.simulator.update_device(room, device_id, status)

                        if success:
                            logger.info(
                                f"Successfully applied action: {room} - {device_id} - {status}"
                            )

                        else:
                            logger.error(
                                f"Failed to apply action: {room} - {device_id} - {status}"
                            )

                    except Exception as e:
                        logger.error(f"Error executing action {action}: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _reproduce_actions: {str(e)}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")

    async def _get_llm_recommendations(self, actions, house_state, current_environment):
        """Получение рекомендаций от LLM для адаптации действий к текущему состоянию"""
        try:
            prompt = """
    You are an AI assistant for a smart home. Based on the user's past actions and current environment, recommend the most appropriate actions to take now. 

    Past user actions during this time of day:
    {actions}

    Current environment:
    {environment}

    Current house state:
    {house_state}

    Given this information, what specific device adjustments should be made right now to maximize user comfort? 
    Consider the following factors:
    1. Time of day and current environment conditions
    2. User's preferences based on their past actions
    3. Optimal comfort settings (temperature 20-24°C, humidity 40-60%)

    VERY IMPORTANT: Return ONLY a valid JSON array of actions in this exact format:
    [
    {{
        "room": "room_type",
        "device_id": "device_id",
        "status": {{"key": value}}
    }}
    ]

    Do not include any explanations, markdown formatting, or text before or after the JSON. Return ONLY the JSON array.
    If you don't recommend any actions, return an empty array: []
    """

            actions_str = json.dumps(actions, indent=2)
            environment_str = json.dumps(current_environment, indent=2)

            house_state_simplified = {
                "time_of_day": self._format_time(house_state.time_minutes),
                "weather": house_state.weather,
                "rooms": {},
            }

            for room_type, room in house_state.rooms.items():
                house_state_simplified["rooms"][room_type] = {"devices": {}}
                for device_id, device in room.devices.items():
                    if not any(
                        sensor in device_id
                        for sensor in [
                            "temp_sensor",
                            "humidity_sensor",
                            "light_sensor",
                            "motion_sensor",
                        ]
                    ):
                        house_state_simplified["rooms"][room_type]["devices"][
                            device_id
                        ] = {"type": device.type, "status": device.status}

            house_state_str = json.dumps(house_state_simplified, indent=2)

            formatted_prompt = prompt.format(
                actions=actions_str,
                environment=environment_str,
                house_state=house_state_str,
            )

            logger.debug("Sending prompt to LLM")

            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI that provides ONLY valid JSON responses without any additional text or explanation.",
                    },
                    {"role": "user", "content": formatted_prompt},
                ],
            )

            recommendations = response["message"]["content"].strip()
            logger.debug(f"Received raw response from LLM: {recommendations[:100]}...")

            import re

            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", recommendations)
            if json_match:
                json_str = json_match.group(1).strip()
                logger.debug(f"Found JSON in code block: {json_str[:100]}...")
            else:
                json_match = re.search(r"\[\s*{[\s\S]*?}\s*\]", recommendations)
                if json_match:
                    json_str = json_match.group(0).strip()
                    logger.debug(f"Found JSON array: {json_str[:100]}...")
                else:
                    json_match = re.search(r"{[\s\S]*?}", recommendations)
                    if json_match:
                        json_str = f"[{json_match.group(0).strip()}]"
                        logger.debug(
                            f"Found JSON object and wrapped in array: {json_str[:100]}..."
                        )
                    else:
                        json_str = recommendations.strip()
                        logger.debug(
                            f"Using entire response as JSON: {json_str[:100]}..."
                        )

            try:
                json_str = json_str.replace("\t", " ").replace("\n", " ")

                actions_data = json.loads(json_str)

                if not isinstance(actions_data, list):
                    logger.warning(f"Expected list, got {type(actions_data)}")
                    if isinstance(actions_data, dict):
                        actions_data = [actions_data]
                    else:
                        logger.warning(
                            f"Cannot convert {type(actions_data)} to list of actions"
                        )
                        return []

                valid_actions = []
                for i, action in enumerate(actions_data):
                    if not isinstance(action, dict):
                        logger.warning(f"Action {i} is not a dictionary: {action}")
                        continue

                    if not all(
                        key in action for key in ["room", "device_id", "status"]
                    ):
                        logger.warning(f"Action {i} missing required fields: {action}")
                        continue

                    if not isinstance(action["room"], str):
                        logger.warning(
                            f"Action {i}: 'room' is not a string: {action['room']}"
                        )
                        continue

                    if not isinstance(action["device_id"], str):
                        logger.warning(
                            f"Action {i}: 'device_id' is not a string: {action['device_id']}"
                        )
                        continue

                    if not isinstance(action["status"], dict):
                        logger.warning(
                            f"Action {i}: 'status' is not a dictionary: {action['status']}"
                        )
                        continue

                    valid_actions.append(action)

                logger.info(
                    f"Validated {len(valid_actions)} actions out of {len(actions_data)}"
                )
                return valid_actions

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.debug(f"Problematic JSON string: {json_str}")

                object_matches = re.findall(r"{[^{}]*}", json_str)
                if object_matches:
                    try:
                        valid_actions = []
                        for obj_str in object_matches:
                            try:
                                obj = json.loads(obj_str)
                                if isinstance(obj, dict) and all(
                                    key in obj
                                    for key in ["room", "device_id", "status"]
                                ):
                                    valid_actions.append(obj)
                            except:
                                continue

                        if valid_actions:
                            logger.info(
                                f"Recovered {len(valid_actions)} actions from partial JSON"
                            )
                            return valid_actions
                    except:
                        pass

                return []

        except Exception as e:
            logger.error(f"Error getting LLM recommendations: {str(e)}")
            return []

    def _get_environment_snapshot(self, house_state):
        """Получение снимка текущего состояния окружающей среды"""
        snapshot = {
            "time_of_day": self._format_time(house_state.time_minutes),
            "weather": house_state.weather,
            "outside_temp": house_state.environment["outside_temp"],
            "outside_humidity": house_state.environment["outside_humidity"],
            "outside_light": house_state.environment["outside_light"],
            "rooms": {},
        }

        for room_type, room in house_state.rooms.items():
            room_data = {}

            for device_id, device in room.devices.items():
                if "sensor" in device_id:
                    room_data[device_id] = device.status.copy()

            snapshot["rooms"][room_type] = room_data

        return snapshot

    def _is_device_changed(self, device_key, current_status):
        """Проверка, изменилось ли состояние устройства"""
        if device_key not in self.last_action_time:
            return True

        prev_status = self.last_action_time[device_key]

        for key, value in current_status.items():
            if key not in prev_status or prev_status[key] != value:
                return True

        return False

    def _format_time(self, time_minutes):
        """Форматирование времени в виде ЧЧ:ММ"""
        h = time_minutes // 60
        m = time_minutes
        return f"{h:02d}:{m:02d}"
