import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import House, RoomType, DeviceUpdateRequest
from simulator import SmartHomeSimulator
import threading

app = FastAPI(title="Smart Home Simulator")

# CORS middleware для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальный экземпляр симулятора
simulator = SmartHomeSimulator()

# Запуск симуляции в отдельном потоке
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulator.start_simulation())

@app.on_event("shutdown")
def shutdown_event():
    simulator.stop_simulation()

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
    success = simulator.update_device(request.room, request.device_id, request.status)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}

@app.post("/api/simulation/speed")
def set_simulation_speed(speed: float):
    """Установить скорость симуляции"""
    if speed not in [1.0, 15.0, 60.0]:
        raise HTTPException(status_code=400, detail="Speed must be 1, 15, or 60")
    simulator.set_simulation_speed(speed)
    return {"success": True, "speed": speed}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
