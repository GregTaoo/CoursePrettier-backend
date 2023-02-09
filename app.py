import shutil
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
import os
import threading

import asyncio
import json

from ShanghaiTechOneAPI.Credential import Credential
from ShanghaiTechOneAPI.Eams import Eams, CourseCalender
from timetable import ICS_Exporter

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class LoginParams(BaseModel):
    userID: str
    password: str

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/login")
async def login(params: LoginParams):
    userID = params.userID
    password = params.password
    try:
        int(userID)
    except ValueError:
        return {
            "isSuccess": False,
            "message": "Invalid userid"
        }
    job_id = str(uuid.uuid4())
    home_dir = os.path.join('./data', job_id)
    table_file = os.path.join(home_dir, 'courseinfo.json')
    try:
        async with Credential(userID) as cred:
            await cred.login(password)
            eams = Eams(cred)
            await eams.login()
            cc = CourseCalender(eams)
            os.makedirs(home_dir, exist_ok=True)
            await cc.get_courseinfo(
                output_file=table_file
            )
    except Exception as e:
        return {
            "isSuccess": False,
            "message": str(e)
        }

    if not os.path.exists(table_file):
        return {
            "isSuccess": False,
            "message": "Table not found",
        }
    try:
        with open(table_file, 'r', encoding='utf-8') as f:
            return {
                "isSuccess": True,
                "message": "OK",
                "id": job_id,
                "table": json.load(f)
            }
    except Exception as e:
        return {
            "isSuccess": False,
            "message": str(e)
        }

@app.get("/api/ics")
async def get_ics(id: str):
    home_dir = os.path.join('./data', id)
    table_file = os.path.join(home_dir, 'courseinfo.json')
    if not os.path.exists(table_file):
        return {
            "isSuccess": False,
            "message": "Table not found"
        }
    ics_file = os.path.join(home_dir, 'courseinfo.ics')
    exporter = ICS_Exporter(start_monday=[2023, 2, 6], calender_name="2022-2023学年2学期")
    exporter.parse_json(table_file)
    exporter.export(ics_file)
    return FileResponse(ics_file, media_type="text/calendar", filename="courseinfo.ics")

