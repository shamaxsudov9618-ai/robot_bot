from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.gpt import ask_gpt, handle_orginfo_query  # 👈 добавили handle_orginfo_query

app = FastAPI(title="Robot backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


class OrgInfoRequest(BaseModel):
    query: str


class OrgInfoResponse(BaseModel):
    answer: str


@app.get("/")
async def root():
    return {"status": "ok", "message": "Robot backend online"}


@app.get("/status")
async def status():
    return {"status": "ok", "mode": "online"}


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest):
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    try:
        answer = await ask_gpt(q)
        return AskResponse(answer=answer)
    except HTTPException:
        raise
    except Exception as e:
        print("Backend /ask error:", e)
        raise HTTPException(status_code=500, detail="OpenAI request failed")


@app.post("/orginfo_query", response_model=OrgInfoResponse)
async def orginfo_endpoint(req: OrgInfoRequest):
    """
    Эндпоинт для режима ORGINFO:
    - принимает свободный текст (ИНН, название, ФИО и т.п.)
    - внутри вызывает handle_orginfo_query из gpt.py
    - возвращает одну или несколько карточек организаций
    """
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        answer = await handle_orginfo_query(q)
        return OrgInfoResponse(answer=answer)
    except HTTPException:
        raise
    except Exception as e:
        print("Backend /orginfo_query error:", e)
        raise HTTPException(status_code=500, detail="Orginfo request failed")


if __name__ == "__main__":
    import uvicorn

    # Локальный запуск:
    # python -m backend.main
    uvicorn.run("backend.main:app", host="0.0.0.0", port=3000)
