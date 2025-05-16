import asyncio
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from simulator.models import House, DeviceUpdateRequest, WeatherType
from simulator.simulator import SmartHomeSimulator
from virtual_user.virtual_user import VirtualUser
from llm_agent.llm_agent import LLMSmartHomeAgent
import asyncio
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

logger = logging.getLogger(__name__)

virtual_user = None
llm_agent = None

app = FastAPI(title="Smart Home Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = SmartHomeSimulator()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulator.start_simulation())


@app.on_event("shutdown")
def shutdown_event():
    simulator.stop_simulation()
    global llm_agent
    if llm_agent and llm_agent.is_active:
        llm_agent.stop()


@app.get("/")
def read_root():
    return {"message": "Smart Home Simulator API"}


@app.get("/api/state", response_model=House)
def get_house_state():
    """Получить текущее состояние дома"""
    return simulator.get_house_state()


@app.post("/api/device")
def update_device(request: DeviceUpdateRequest):
    """Обновить состояние устройства"""
    logger.info(f"Device update request: {request.dict()}")

    house_state = simulator.get_house_state()
    if request.room in house_state.rooms:
        room = house_state.rooms[request.room]
        if request.device_id in room.devices:
            device = room.devices[request.device_id]
            logger.debug(
                f"Device found: {device.type}, current status: {device.status}"
            )
        else:
            logger.warning(
                f"Device {request.device_id} not found in room {request.room}"
            )
    else:
        logger.warning(f"Room {request.room} not found")

    success = simulator.update_device(request.room, request.device_id, request.status)
    if not success:
        logger.error(
            f"Failed to update device: {request.device_id} in {request.room} with status {request.status}"
        )
        raise HTTPException(
            status_code=404, detail="Device not found or invalid status"
        )

    return {"success": True}


@app.post("/api/simulation/speed")
def set_simulation_speed(data: dict):
    """Установить скорость симуляции"""
    speed = data.get("speed")

    if speed is None:
        raise HTTPException(status_code=400, detail="Speed parameter is required")

    try:
        speed = float(speed)
    except ValueError:
        raise HTTPException(status_code=400, detail="Speed must be a number")

    if speed not in [1.0, 15.0, 60.0, 3600.0]:
        raise HTTPException(
            status_code=400, detail="Speed must be 1.0, 15.0, 60.0, or 3600.0"
        )

    success = simulator.set_simulation_speed(speed)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to set simulation speed")

    return {"success": True, "speed": speed}


@app.get("/api/time")
def get_time():
    """Получить текущее время симуляции и погоду"""
    minutes = simulator.house.time_minutes
    hours = minutes // 60
    mins = minutes % 60

    return {
        "hours": hours,
        "minutes": mins,
        "time_of_day": simulator.house.time_of_day,
        "formatted": f"{hours:02d}:{mins:02d}",
        "weather": simulator.house.weather,
    }


@app.post("/api/weather")
def set_weather(data: dict):
    """Установить погоду"""
    weather = data.get("weather")

    if not weather or weather not in ["sunny", "cloudy", "rainy"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid weather. Must be 'sunny', 'cloudy', or 'rainy'",
        )

    success = simulator.set_weather(WeatherType(weather))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set weather")

    return {"success": True, "weather": weather}


@app.post("/api/virtual_user/start")
async def start_virtual_user():
    """Запуск виртуального пользователя"""
    global virtual_user

    if virtual_user is not None and virtual_user.is_active:
        return {"message": "Virtual user is already running"}

    virtual_user = VirtualUser()

    threading.Thread(
        target=asyncio.run, args=(virtual_user.start(simulator),), daemon=True
    ).start()

    return {"message": "Virtual user started"}


@app.post("/api/virtual_user/stop")
def stop_virtual_user():
    """Остановка виртуального пользователя"""
    global virtual_user

    if virtual_user is None or not virtual_user.is_active:
        return {"message": "Virtual user is not running"}

    virtual_user.stop()
    return {"message": "Virtual user stopped"}


@app.get("/api/virtual_user/status")
def get_virtual_user_status():
    """Получение статуса виртуального пользователя"""
    global virtual_user

    if virtual_user is None:
        return {"active": False}

    status = virtual_user.get_status()
    status["active"] = virtual_user.is_active

    return status


@app.post("/api/llm_agent/start")
async def start_llm_agent():
    """Запуск LLM агента для умного дома"""
    global llm_agent

    if llm_agent is not None and llm_agent.is_active:
        return {"message": "LLM agent is already running"}

    llm_agent = LLMSmartHomeAgent()

    threading.Thread(
        target=asyncio.run, args=(llm_agent.start(simulator),), daemon=True
    ).start()

    return {"message": "LLM agent started"}


@app.post("/api/llm_agent/stop")
def stop_llm_agent():
    """Остановка LLM агента"""
    global llm_agent

    if llm_agent is None or not llm_agent.is_active:
        return {"message": "LLM agent is not running"}

    llm_agent.stop()
    return {"message": "LLM agent stopped"}


@app.get("/api/llm_agent/status")
def get_llm_agent_status():
    """Получение статуса LLM агента"""
    global llm_agent

    if llm_agent is None:
        return {"active": False}

    days_passed = simulator.house.days_passed

    return {
        "active": llm_agent.is_active,
        "observation_day": llm_agent.observation_day,
        "days_passed": days_passed,
        "actions_recorded": len(llm_agent.user_actions),
    }


app.mount("/reports", StaticFiles(directory="reports"), name="reports")


@app.get("/api/reports")
def get_reports():
    """Получить список доступных отчетов"""
    try:
        if not os.path.exists("reports"):
            return {"days": []}

        day_dirs = [
            d
            for d in os.listdir("reports")
            if os.path.isdir(os.path.join("reports", d))
        ]

        reports_info = []
        for day_dir in day_dirs:
            day_path = os.path.join("reports", day_dir)
            files = os.listdir(day_path)

            csv_files = [f for f in files if f.endswith(".csv")]
            image_files = [f for f in files if f.endswith(".png")]

            reports_info.append(
                {"day_id": day_dir, "csv_files": csv_files, "image_files": image_files}
            )

        return {"days": reports_info}
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        return {"days": [], "error": str(e)}


@app.get("/api/reports/{day_id}/{file_name}")
def get_report_file(day_id: str, file_name: str):
    """Получить конкретный файл отчета"""
    file_path = os.path.join("reports", day_id, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(file_path)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
