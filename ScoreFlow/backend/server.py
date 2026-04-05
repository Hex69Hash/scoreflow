from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import hashlib
import base64
import io
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

CURRENT_YEAR = datetime.now(timezone.utc).year

SEBA_CONFIG = {
    "name": "SEBA",
    "exam": "HSLC",
    "full_name": "Board of Secondary Education, Assam",
    "result_url": "https://sebaonline.org/results",
    "latest_released_year": 2025,
    "expected_release_note": "Expected: June 2026",
}

AHSEC_CONFIG = {
    "name": "AHSEC",
    "exam": "HS",
    "full_name": "Assam Higher Secondary Education Council",
    "result_url": "https://ahsec.assam.gov.in/results",
    "is_current_year_released": False,
    "latest_released_year": 2025,
    "expected_release_note": "Expected: June 2026",
}

ROLL_SEBA = re.compile(r'^[A-Z]\d{2}-\d{4}$')

FIRST_NAMES = [
    "Aman", "Priya", "Rahul", "Shreya", "Deepak", "Ankita", "Vikash",
    "Riya", "Sanjay", "Meera", "Bhaskar", "Diya", "Arjun", "Nisha",
    "Kamal", "Pooja", "Manish", "Jyoti", "Rohit", "Ananya",
]
LAST_NAMES = [
    "Das", "Sharma", "Bora", "Kalita", "Nath", "Baruah", "Hazarika",
    "Gogoi", "Saikia", "Deka", "Choudhury", "Medhi", "Pathak",
    "Bhuyan", "Sarma",
]
SEBA_SUBJECTS = [
    "English", "Assamese (MIL)", "Mathematics",
    "General Science", "Social Science", "Hindi (Elective)",
]
AHSEC_SUBJECTS = [
    "English", "Assamese (MIL)", "Physics",
    "Chemistry", "Mathematics", "Computer Science",
]


def generate_sample_result(board: str, roll: str, number: str):
    seed = hashlib.md5(f"{board}:{roll}:{number}".encode()).hexdigest()
    s = int(seed[:8], 16)
    name = f"{FIRST_NAMES[s % len(FIRST_NAMES)]} {LAST_NAMES[(s // 100) % len(LAST_NAMES)]}"
    subjects = SEBA_SUBJECTS if board == "seba" else AHSEC_SUBJECTS
    marks = []
    for i, subj in enumerate(subjects):
        sub_s = (s + i * 7919 + i * i * 31) % 100
        mark = max(28, min(97, 45 + (sub_s % 50)))
        marks.append({"subject": subj, "marks": mark, "full_marks": 100})
    total = sum(m["marks"] for m in marks)
    full_total = len(marks) * 100
    pct = round((total / full_total) * 100, 2)
    passed = all(m["marks"] >= 30 for m in marks) and pct >= 30
    return {
        "student_name": name,
        "subjects": marks,
        "total_marks": total,
        "full_total_marks": full_total,
        "percentage": pct,
        "result_status": "PASS" if passed else "FAIL",
    }


def normalize_seba_roll(raw: str) -> str:
    val = raw.strip().upper().replace(" ", "")
    if len(val) == 7 and val[0].isalpha() and val[1:3].isdigit() and val[3:7].isdigit() and '-' not in val:
        val = val[:3] + '-' + val[3:]
    return val


def extract_year(roll: str) -> int:
    try:
        return 2000 + int(roll[1:3])
    except (ValueError, IndexError):
        return 0


class CheckResultRequest(BaseModel):
    board: str
    roll: str
    number: str
    registration_number: Optional[str] = None


@api_router.get("/")
async def root():
    return {"message": "Assam Board Results Portal API"}


@api_router.get("/config")
async def get_config():
    return {
        "current_year": CURRENT_YEAR,
        "seba": {"latest_released_year": SEBA_CONFIG["latest_released_year"]},
        "ahsec": {
            "is_current_year_released": AHSEC_CONFIG["is_current_year_released"],
            "latest_released_year": AHSEC_CONFIG["latest_released_year"],
        },
    }


@api_router.post("/check-result")
async def check_result(req: CheckResultRequest):
    bk = req.board.lower()

    if bk == "seba":
        roll = normalize_seba_roll(req.roll)
        num = req.number.strip()
        if not roll:
            return {"success": False, "error": "Please enter your roll number", "error_type": "validation"}
        if not ROLL_SEBA.match(roll):
            return {"success": False, "error": "Roll must match format BXX-XXXX (e.g., B26-0816)", "error_type": "validation"}
        if not num:
            return {"success": False, "error": "Please enter your number", "error_type": "validation"}
        if not num.isdigit():
            return {"success": False, "error": "Number must contain only digits", "error_type": "validation"}
        if len(num) < 3:
            return {"success": False, "error": "Number must be at least 3 digits", "error_type": "validation"}

        year = extract_year(roll)
        exam = f"{SEBA_CONFIG['exam']} Examination Result {year}"

        if year > SEBA_CONFIG["latest_released_year"]:
            await _log(bk, roll, num, None, year, "not_released")
            return {
                "success": False, "error_type": "not_released",
                "title": "Result Not Released", "subtitle": exam,
                "message": "Results have not been announced yet. Please check later.",
                "note": SEBA_CONFIG["expected_release_note"], "year": year,
            }
        if year < 2024:
            await _log(bk, roll, num, None, year, "unsupported")
            return {"success": False, "error_type": "unsupported_year",
                    "error": "Results for this year are not available here. Please use official websites.", "year": year}

        sample = generate_sample_result(bk, roll, num)
        await _log(bk, roll, num, None, year, "success")
        return {
            "success": True, "result_url": SEBA_CONFIG["result_url"],
            "board_name": SEBA_CONFIG["name"], "exam_name": exam,
            "full_name": SEBA_CONFIG["full_name"],
            "roll": roll, "number": num, "year": year, **sample,
        }

    elif bk == "ahsec":
        roll = req.roll.strip()
        num = req.number.strip()
        reg = (req.registration_number or "").strip()
        if not roll:
            return {"success": False, "error": "Please enter your roll number", "error_type": "validation"}
        if not roll.isdigit():
            return {"success": False, "error": "Roll must contain only digits", "error_type": "validation"}
        if not num:
            return {"success": False, "error": "Please enter your number", "error_type": "validation"}
        if not num.isdigit():
            return {"success": False, "error": "Number must contain only digits", "error_type": "validation"}
        if not reg:
            return {"success": False, "error": "Please enter your registration number", "error_type": "validation"}
        if not reg.isdigit():
            return {"success": False, "error": "Registration number must contain only digits", "error_type": "validation"}

        exam = f"{AHSEC_CONFIG['exam']} Examination Result {CURRENT_YEAR}"
        if not AHSEC_CONFIG["is_current_year_released"]:
            await _log(bk, roll, num, reg, CURRENT_YEAR, "not_released")
            return {
                "success": False, "error_type": "not_released",
                "title": "Result Not Released", "subtitle": exam,
                "message": "Results have not been announced yet. Please check later.",
                "note": AHSEC_CONFIG["expected_release_note"], "year": CURRENT_YEAR,
            }

        sample = generate_sample_result(bk, roll, num)
        await _log(bk, roll, num, reg, CURRENT_YEAR, "success")
        return {
            "success": True, "result_url": AHSEC_CONFIG["result_url"],
            "board_name": AHSEC_CONFIG["name"], "exam_name": exam,
            "full_name": AHSEC_CONFIG["full_name"],
            "roll": roll, "number": num, "registration_number": reg,
            "year": CURRENT_YEAR, **sample,
        }

    return {"success": False, "error": "Invalid board selected", "error_type": "validation"}


@api_router.post("/generate-image")
async def generate_image(data: dict):
    try:
        from PIL import Image, ImageDraw, ImageFont

        w, h = 800, 1100
        img = Image.new('RGB', (w, h), 'white')
        draw = ImageDraw.Draw(img)
        try:
            ft = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            fr = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            f_title = ImageFont.truetype(ft, 20)
            f_head = ImageFont.truetype(ft, 15)
            f_body = ImageFont.truetype(fr, 14)
            f_sm = ImageFont.truetype(fr, 11)
        except Exception:
            f_title = f_head = f_body = f_sm = ImageFont.load_default()

        # Header
        draw.rectangle([0, 0, w, 80], fill='#003B73')
        draw.text((w // 2, 18), "ASSAM BOARD RESULTS PORTAL", fill='white', font=f_title, anchor='mt')
        draw.text((w // 2, 48), data.get("exam_name", ""), fill='#B0C4DE', font=f_sm, anchor='mt')

        # Border
        draw.rectangle([30, 95, w - 30, h - 30], outline='#003B73', width=2)

        # Board
        y = 112
        draw.text((50, y), data.get("full_name", ""), fill='#003B73', font=f_head)
        y += 28
        draw.line([(50, y), (w - 50, y)], fill='#D1D5DB')

        # Details
        y += 14
        pairs = [
            ("Student Name", data.get("student_name", "")),
            ("Roll", data.get("roll", "")),
            ("Number", data.get("number", "")),
        ]
        if data.get("registration_number"):
            pairs.append(("Reg No", data["registration_number"]))
        pairs.append(("Year", str(data.get("year", ""))))

        for lbl, val in pairs:
            draw.text((50, y), f"{lbl}:", fill='#6B7280', font=f_body)
            draw.text((200, y), val, fill='#111827', font=f_head)
            y += 26

        # Table
        y += 16
        draw.rectangle([50, y, w - 50, y + 32], fill='#003B73')
        draw.text((70, y + 7), "Subject", fill='white', font=f_head)
        draw.text((w - 140, y + 7), "Marks", fill='white', font=f_head)
        y += 32

        for i, sub in enumerate(data.get("subjects", [])):
            bg = '#F0F4F8' if i % 2 == 0 else '#FFFFFF'
            draw.rectangle([50, y, w - 50, y + 30], fill=bg)
            draw.line([(50, y), (w - 50, y)], fill='#E5E7EB')
            draw.text((70, y + 6), sub.get("subject", ""), fill='#111827', font=f_body)
            draw.text((w - 140, y + 6), f"{sub.get('marks', 0)} / {sub.get('full_marks', 100)}", fill='#111827', font=f_body)
            y += 30

        draw.line([(50, y), (w - 50, y)], fill='#003B73', width=2)

        # Summary
        y += 18
        draw.text((70, y), f"Total Marks:  {data.get('total_marks', 0)} / {data.get('full_total_marks', 600)}", fill='#111827', font=f_head)
        y += 28
        draw.text((70, y), f"Percentage:  {data.get('percentage', 0)}%", fill='#111827', font=f_head)
        y += 28
        status = data.get("result_status", "")
        sc = '#16A34A' if status == 'PASS' else '#DC2626'
        draw.text((70, y), "Result:", fill='#111827', font=f_head)
        bx = 170
        draw.rounded_rectangle([bx, y - 3, bx + 80, y + 22], radius=4, fill=sc)
        draw.text((bx + 40, y + 2), status, fill='white', font=f_head, anchor='mt')

        # Footer
        y = h - 65
        draw.line([(50, y), (w - 50, y)], fill='#D1D5DB')
        y += 12
        draw.text((w // 2, y), "Verify this result on the official board website", fill='#9CA3AF', font=f_sm, anchor='mt')
        y += 16
        draw.text((w // 2, y), "Assam Board Results Portal", fill='#9CA3AF', font=f_sm, anchor='mt')

        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return {"success": True, "image": b64}
    except Exception as e:
        logger.error(f"Image gen error: {e}")
        return {"success": False, "error": str(e)}


async def _log(board, roll, number, reg, year, status):
    await db.result_checks.insert_one({
        "id": str(uuid.uuid4()), "board": board, "roll": roll,
        "number": number, "registration_number": reg,
        "year": year, "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@api_router.get("/stats")
async def get_stats():
    total = await db.result_checks.count_documents({})
    return {"total_checks": total}


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
