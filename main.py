from fastapi import FastAPI
import uvicorn

# Inclui rotas do controller
from controller.generate_controller import router as generate_router

app = FastAPI(title="BiometryEngine API")

# Inclui o router principal (sem prefixo)
app.include_router(generate_router)


if __name__ == "__main__":
    # Para desenvolvimento rápido
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
