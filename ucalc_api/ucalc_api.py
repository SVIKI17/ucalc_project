from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ucalc_api.ucalc_config import WEB_DIR
from ucalc_api.ucalc_db import SessionLocal, UcalcHistory, UcalcUnit, init_db
from ucalc_api import ucalc_dropbox

app = FastAPI(title="ucalc API")
init_db()

templates = Jinja2Templates(directory=str(WEB_DIR))
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class ConvertRequest(BaseModel):
    category: str
    from_code: str
    to_code: str
    value: float
    precision: int = 2
    save: bool = False


def convert_value(from_unit: UcalcUnit, to_unit: UcalcUnit, value: float) -> float:
    base = value * from_unit.factor + from_unit.offset
    return (base - to_unit.offset) / to_unit.factor


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ucalc/categories")
def list_categories():
    with SessionLocal() as db:
        rows = db.query(UcalcUnit.category).distinct().all()
    return {"categories": [r[0] for r in rows]}


@app.get("/api/ucalc/units")
def list_units(category: str):
    with SessionLocal() as db:
        units = db.query(UcalcUnit).filter(UcalcUnit.category == category).all()
    return {
        "units": [
            {"code": u.code, "name": u.name, "factor": u.factor, "offset": u.offset}
            for u in units
        ]
    }


@app.post("/api/ucalc/convert")
def do_convert(req: ConvertRequest):
    with SessionLocal() as db:
        frm = db.query(UcalcUnit).filter(UcalcUnit.code == req.from_code).first()
        to = db.query(UcalcUnit).filter(UcalcUnit.code == req.to_code).first()
        if not frm or not to or frm.category != req.category or to.category != req.category:
            raise HTTPException(status_code=400, detail="invalid units")
        raw = convert_value(frm, to, req.value)
        result = round(raw, req.precision)

        if req.save:
            db.add(UcalcHistory(
                category=req.category,
                from_code=req.from_code,
                to_code=req.to_code,
                input_value=req.value,
                result_value=result,
                precision=req.precision,
            ))
            db.commit()

    return {"result": result, "precision": req.precision, "saved": req.save}


@app.get("/api/ucalc/history")
def get_history():
    with SessionLocal() as db:
        rows = (
            db.query(UcalcHistory)
            .order_by(UcalcHistory.id.desc())
            .limit(20)
            .all()
        )
    return {
        "history": [
            {
                "id": r.id,
                "category": r.category,
                "from_code": r.from_code,
                "to_code": r.to_code,
                "input_value": r.input_value,
                "result_value": r.result_value,
                "precision": r.precision,
                "created_at": r.created_at.isoformat(timespec="seconds"),
            }
            for r in rows
        ]
    }


@app.delete("/api/ucalc/history")
def clear_history():
    with SessionLocal() as db:
        db.query(UcalcHistory).delete()
        db.commit()
    return {"status": "cleared"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "ucalc_index.html")


from fastapi.responses import JSONResponse

@app.get("/api/ucalc/dropbox/info")
def dropbox_info():
    try:
        return ucalc_dropbox.get_user_info()
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/ucalc/dropbox/space")
def dropbox_space():
    try:
        return ucalc_dropbox.get_space_usage()
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/ucalc/dropbox/list")
def dropbox_list(path: str = ""):
    try:
        return ucalc_dropbox.list_folder(path)
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.post("/api/ucalc/dropbox/export")
def dropbox_export():
    """Экспорт всей истории в JSON и загрузка на Dropbox."""
    import json
    with SessionLocal() as db:
        rows = db.query(UcalcHistory).order_by(UcalcHistory.id.desc()).all()
    payload = {
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds"),
        "count": len(rows),
        "history": [
            {
                "id": r.id,
                "category": r.category,
                "from_code": r.from_code,
                "to_code": r.to_code,
                "input_value": r.input_value,
                "result_value": r.result_value,
                "precision": r.precision,
                "created_at": r.created_at.isoformat(timespec="seconds"),
            }
            for r in rows
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        ucalc_dropbox.ensure_folder("/ucalc_exports")
        up = ucalc_dropbox.upload_file(body, "/ucalc_exports/history.json")
        link = ucalc_dropbox.create_shared_link("/ucalc_exports/history.json")
        return {"uploaded": up, "link": link}
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})