import base64
import os

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ShanghaiTechOneAPI.Credential import Credential
from ShanghaiTechOneAPI.Eams import Eams
from timetable import ICS_Exporter


class LoginParams(BaseModel):
    userID: str
    password: str

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def return_message(success: bool, message: str=None) -> dict:
    return {
        "isSuccess": success,
        "message": message
    } if message is not None else {
        "isSuccess": success
    }

@app.post("/api/login")
async def login(params: LoginParams, response: Response):
    user_id, password = params.userID, params.password
    try:
        int(user_id)
    except ValueError:
        return return_message(False, "Invalid UserID")
    try:
        async with Credential(user_id) as cred:
            await cred.login(password)
            eams = Eams(cred)
            await eams.login()
            if cred.is_login:
                cookie_str = ''
                for cookie in cred.session.cookie_jar:
                    cookie_str += base64.b64encode(cookie.__str__().encode("utf-8")).decode("utf-8") + ':'
                response.set_cookie('LOGIN_SESSION', cookie_str, max_age=7776000)
                return return_message(True)
    except Exception as e:
        return return_message(False, str(e))

# @app.post("/api/login")
# async def login(params: LoginParams):
#     user_id = params.userID
#     password = params.password
#     try:
#         int(user_id)
#     except ValueError:
#         return {
#             "isSuccess": False,
#             "message": "Invalid userid"
#         }
#     job_id = str(uuid.uuid4())
#     home_dir = os.path.join('./data', job_id)
#     table_file = os.path.join(home_dir, 'courseinfo.json')
#     try:
#         async with Credential(user_id) as cred:
#             await cred.login(password)
#             eams = Eams(cred)
#             await eams.login()
#             cc = CourseCalender(eams)
#             os.makedirs(home_dir, exist_ok=True)
#             await cc.get_courseinfo(
#                 output_file=table_file,
#                 work_dir=home_dir
#             )
#     except Exception as e:
#         return {
#             "isSuccess": False,
#             "message": str(e)
#         }
#
#     if not os.path.exists(table_file):
#         return {
#             "isSuccess": False,
#             "message": "Table not found",
#         }
#     try:
#         with open(table_file, 'r', encoding='utf-8') as f:
#             return {
#                 "isSuccess": True,
#                 "message": "OK",
#                 "id": job_id,
#                 "table": json.load(f)
#             }
#     except Exception as e:
#         return {
#             "isSuccess": False,
#             "message": str(e)
#         }

@app.get("/api/ics")
async def get_ics(id: str):
    if id == "":
        return HTTPException(status_code=400, detail="Invalid id")
    home_dir = os.path.join('./data', id)
    table_file = os.path.join(home_dir, 'courseinfo.json')
    if not os.path.exists(table_file):
        return HTTPException(status_code=404, detail="Table not found")
    ics_file = os.path.join(home_dir, 'courseinfo.ics')
    exporter = ICS_Exporter(start_monday=[2025, 2, 17], calender_name="2024-2025学年2学期")
    exporter.parse_json(table_file)
    exporter.export(ics_file)
    return FileResponse(ics_file, media_type="text/calendar", filename="courseinfo.ics")

