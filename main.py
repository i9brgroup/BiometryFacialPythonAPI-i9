import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# Inclui rotas do controller
from controller.generate_controller import router as generate_router

app = FastAPI(title="BiometryEngine API")

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # ou ["*"] apenas em dev
    allow_credentials=True,
    allow_methods=["*"],             # permite OPTIONS, POST, GET, etc.
    allow_headers=["*"],             # ou listar explicitamente ["Authorization","Content-Type","Accept"]
)

# Inclui o router principal (sem prefixo)
app.include_router(generate_router)


if __name__ == "__main__":
    # Para desenvolvimento rápido
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
